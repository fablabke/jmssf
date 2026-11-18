#!/usr/bin/env python3
"""
MQTT Logger - Enregistre tous les messages d'un channel MQTT dans un fichier texte.

Format de log : [YYYY-MM-DD HH:MM:SS.mmm] (topic) : message

Dépendances :
    pip install paho-mqtt
"""

import argparse
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt


class MQTTLogger:
    def __init__(
        self,
        broker: str,
        port: int,
        topics: list[str],
        log_file: str,
        username: str | None = None,
        password: str | None = None,
        qos: int = 0,
        use_tls: bool = False,
        client_id: str | None = None,
    ):
        self.broker = broker
        self.port = port
        self.topics = topics
        self.log_file = Path(log_file)
        self.qos = qos
        self.use_tls = use_tls
        self.client_id = client_id or f"mqtt-logger-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Créer le dossier parent si nécessaire
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Ouvrir le fichier de log en mode append (buffering ligne par ligne)
        self.fp = open(self.log_file, "a", encoding="utf-8", buffering=1)

        # Client MQTT
        self.client = mqtt.Client(client_id=self.client_id, clean_session=True)

        if username:
            self.client.username_pw_set(username, password)

        if self.use_tls:
            self.client.tls_set()  # Utilise les CA système par défaut

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe

    # ---------- Callbacks ----------
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("✅ Connecté au broker %s:%d", self.broker, self.port)
            for topic in self.topics:
                client.subscribe(topic, qos=self.qos)
                logging.info("📡 Abonné à : %s (QoS=%d)", topic, self.qos)
        else:
            logging.error("❌ Échec de connexion, code : %s", rc)

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        logging.debug("Subscription confirmed (mid=%s, qos=%s)", mid, granted_qos)

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.warning("⚠️ Déconnexion inattendue (code=%s), reconnexion automatique...", rc)
        else:
            logging.info("🔌 Déconnecté proprement du broker.")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
        except Exception as e:
            payload = f"<binary: {len(msg.payload)} bytes, erreur décodage: {e}>"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] ({msg.topic}) : {payload}"

        # Écriture dans le fichier
        self.fp.write(line + "\n")

        # Affichage console également
        print(line)

    # ---------- Contrôle ----------
    def start(self):
        logging.info("🚀 Connexion à %s:%d ...", self.broker, self.port)
        # loop_forever gère automatiquement les reconnexions
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_forever(retry_first_connection=True)

    def stop(self, *args):
        logging.info("🛑 Arrêt demandé, déconnexion...")
        try:
            self.client.disconnect()
            self.client.loop_stop()
        finally:
            self.fp.close()
        sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Logge tous les messages MQTT d'un ou plusieurs topics dans un fichier texte."
    )
    parser.add_argument("--broker", "-b", default="localhost", help="Adresse du broker MQTT (défaut: localhost)")
    parser.add_argument("--port", "-p", type=int, default=1883, help="Port du broker (défaut: 1883)")
    parser.add_argument(
        "--topic", "-t", action="append", required=True,
        help="Topic à écouter (wildcards + et # supportés). Peut être répété plusieurs fois."
    )
    parser.add_argument(
        "--file", "-f", default="mqtt_log.txt", help="Fichier de log (défaut: mqtt_log.txt)"
    )
    parser.add_argument("--username", "-u", default=None, help="Nom d'utilisateur MQTT")
    parser.add_argument("--password", "-P", default=None, help="Mot de passe MQTT")
    parser.add_argument("--qos", "-q", type=int, default=0, choices=[0, 1, 2], help="QoS (défaut: 0)")
    parser.add_argument("--tls", action="store_true", help="Activer TLS")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logs détaillés")
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = MQTTLogger(
        broker=args.broker,
        port=args.port,
        topics=args.topic,
        log_file=args.file,
        username=args.username,
        password=args.password,
        qos=args.qos,
        use_tls=args.tls,
    )

    # Interception Ctrl+C et SIGTERM pour fermeture propre du fichier
    signal.signal(signal.SIGINT, logger.stop)
    signal.signal(signal.SIGTERM, logger.stop)

    try:
        logger.start()
    except KeyboardInterrupt:
        logger.stop()
    except Exception as e:
        logging.error("Erreur fatale : %s", e, exc_info=True)
        logger.stop()


if __name__ == "__main__":
    main()
