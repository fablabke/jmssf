import network
import time
from umqtt.robust import MQTTClient
import time
import machine

# l'imprimante se connecte au channel 'jmssf/print' sur test.mosquitto.org
#todo : info à compléter !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
wifi_network = 'fablabke4g' 
wifi_password = 'fablabke4g'
nom_groupe = 'nom-de-votre-groupe'
nom_topic = 'jmssf/print'

# défini la liaison série avec l'imprimante, elle doit être branchée sur les pin 0 (fil vert) et pin 1 (fil jaune)
printer = machine.UART(0, baudrate=9600, tx=machine.Pin(0), rx=machine.Pin(1))
printer.write(b'\x1b\x40')
printer.write('connecte a ' + wifi_network)
printer.write(b'\n') # ça c'est un saut de ligne

# connexion au wifi
sta_if = network.WLAN(network.STA_IF); sta_if.active(True)
sta_if.scan()
sta_if.connect(wifi_network, wifi_password)
print("Attente connexion wifi sur", wifi_network)
printer.write("Attente connexion wifi sur", wifi_network)
printer.write(b'\n')


i = 0
while not sta_if.isconnected():
    time.sleep(i)
    i += 0.5
    print(i)
print("Connecté au wifi")
printer.write("Connecté au wifi")
printer.write(b'\n')


# Création du client MQTT
mqtt = MQTTClient(nom_groupe, 'test.mosquitto.org')

def mqtt_callback(topic, message):
    print(">>> MESSAGE RECU :", topic, repr(message))
    printer.write(message)
    printer.write(b'\n')

mqtt.set_callback(mqtt_callback)

mqtt.connect()

print("Connecte au Mosquitto")
printer.write("Connecte au Mosquitto")
printer.write(b'\n')

resultat = mqtt.subscribe(b'jmssf/print')
print("Abonnement au topic", nom_topic)
printer.write("Abonnement au topic", nom_topic)
printer.write(b'\n')

while True:
    try:
        mqtt.check_msg()
        time.sleep_ms(100)
    except Exception as e:
        print("Erreur MQTT :", repr(e))
        time.sleep(2)