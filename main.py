from typing import List

import rrdtool
import os
from pysnmp.hlapi import *
import time
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

def consultaSNMP(comunidad:str,host:str, oid:str, version:int):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        # hace la solicitud getsnmp
        getCmd(SnmpEngine(),
               CommunityData(comunidad, mpModel=version),
               UdpTransportTarget((host, 161)),  # udp
               ContextData(),
               ObjectType(ObjectIdentity(oid))))

    if errorIndication:
        pass
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            varB = (' = '.join([x.prettyPrint() for x in varBind]))
            resultado = varB.split()[2]  # se agarra la ultima parte de la consulta
        return resultado

def RDD(direccion: str,nombreRRD: str):
    ret = rrdtool.create("/home/dannytupapi/PycharmProjects/Practica3/"+direccion+"/"+nombreRRD,
                            "--start",'N',
                            "--step",'30',
                            "DS:CPUload:GAUGE:60:0:100",  # DS: Octetos de entrada :
                            "RRA:AVERAGE:0.5:1:35")   # RRA: Cada 60 segs de hace un AVERAGE:

    if ret:
        print(rrdtool.error())



def UPDATERRD(comunity:str, hostname:str, version):
    lista = [0,0,0]
    lista[0] = consultaSNMP(comunity, hostname, '1.3.6.1.2.1.25.3.3.1.2.196608', version)
    valor = "N:" + str(lista[0])
    rrdtool.update(comunity + '_' + hostname + '/trend.rrd', valor)

    lista[1] = int(consultaSNMP(comunity, hostname, '1.3.6.1.4.1.2021.4.6.0', version))
    ram = "{:.2f}".format(lista[1] * 1e-6)
    valor = "N:" + str(ram)
    rrdtool.update(comunity + '_' + hostname + '/trend2.rrd', valor)

    lista[2] = int(consultaSNMP(comunity, hostname, '1.3.6.1.2.1.25.2.3.1.6.1', version))
    storage = "{:.2f}".format(lista[2] * 1e-6)
    valor = "N:" + str(storage)
    rrdtool.update(comunity + '_' + hostname + '/trend3.rrd', valor)

    time.sleep(5)

    return lista

def GENERARGRAFICAS(comunity:str, hostname:str):
    GRAFICAUMBRAL(comunity,hostname, 'trend.rrd')
    GRAFICAUMBRALRAM(comunity, hostname, 'trend2.rrd')
    GRAFICAUMBRALSTORAGE(comunity,hostname,'trend3.rrd')

def GRAFICAUMBRAL(comunity:str, hostname:str, name:str):
    rrdpath = comunity + '_' + hostname + '/'
    imgpath = comunity + '_' + hostname + '/'

    ultima_lectura = int(rrdtool.last(rrdpath + name))
    tiempo_final = ultima_lectura
    tiempo_inicial = tiempo_final - 120

    ret = rrdtool.graphv(imgpath + "deteccionCPU.png",
                         "--start", str(tiempo_inicial),
                         "--end", str(tiempo_final),
                         "--vertical-label=Cpu load",
                         '--lower-limit', '0',
                         '--upper-limit', '20',
                         "--title=Uso del CPU del agente Usando SNMP y RRDtools \n Detección de umbrales",

                         "DEF:cargaCPU=" + rrdpath + "trend.rrd:CPUload:AVERAGE",
                         # DEF permite generar una variable de tipo colección
                         # VDEF genera un punto con la entrada de una colección
                         "VDEF:cargaMAX=cargaCPU,MAXIMUM",  # el punto maximo
                         "VDEF:cargaMIN=cargaCPU,MINIMUM",  # el punto minimo
                         "VDEF:cargaSTDEV=cargaCPU,STDEV",  # punto de desviación estandar
                         "VDEF:cargaLAST=cargaCPU,LAST",  # ultimo punto almacenado

                         # "CDEF:Coleccion=cargaCPU,8,*",   #obtiene los octetos de entrada y lo multiplica por 8
                         "CDEF:umbral18=cargaCPU,18,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 15
                         "CDEF:umbral22=cargaCPU,22,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 15
                         "CDEF:umbral28=cargaCPU,28,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 15

                         "AREA:cargaCPU#00FF00:Carga de la CPU",
                         "AREA:umbral18#CC9900:Carga CPU mayor que 18",
                         "AREA:umbral22#FFB74D:Carga CPU mayor que 22",
                         "AREA:umbral28#FF5722:Carga CPU mayor que 28",

                         "HRULE:18#CC9900:Umbral 1 - 18%",  # marca de umbral de 18
                         "HRULE:22#FFB74D:Umbral 1 - 22%",  # marca de umbral de 22
                         "HRULE:28#FF5722:Umbral 1 - 28%",  # marca de umbral de 28

                         "PRINT:cargaLAST:%6.2lf",
                         "GPRINT:cargaMIN:%6.2lf %SMIN",
                         "GPRINT:cargaSTDEV:%6.2lf %SSTDEV",
                         "GPRINT:cargaLAST:%6.2lf %SLAST")
    print(ret)

    ultimo_valor = float(ret['print[0]'])
    if ultimo_valor > 4:
        send_alert_attached("Sobrepasa Umbral línea base", "deteccionCPU.png", comunity, hostname, name)
        print("Sobrepasa Umbral línea base")



def GRAFICAUMBRALRAM(comunity:str, hostname:str, name:str):
    rrdpath = comunity + '_' + hostname + '/'
    imgpath = comunity + '_' + hostname + '/'

    ultima_lectura = int(rrdtool.last(rrdpath + name))
    tiempo_final = ultima_lectura
    tiempo_inicial = tiempo_final - 120

    ret = rrdtool.graphv(imgpath + "deteccionRAM.png",
                         "--start", str(tiempo_inicial),
                         "--end", str(tiempo_final),
                         "--vertical-label=Cpu load",
                         '--lower-limit', '0',
                         '--upper-limit', '.4',
                         "--title=Uso de la RAM del agente Usando SNMP y RRDtools \n Detección de umbrales",

                         "DEF:cargaCPU=" + rrdpath + "trend2.rrd:CPUload:AVERAGE",
                         # DEF permite generar una variable de tipo colección
                         # VDEF genera un punto con la entrada de una colección
                         "VDEF:cargaMAX=cargaCPU,MAXIMUM",  # el punto maximo
                         "VDEF:cargaMIN=cargaCPU,MINIMUM",  # el punto minimo
                         "VDEF:cargaSTDEV=cargaCPU,STDEV",  # punto de desviación estandar
                         "VDEF:cargaLAST=cargaCPU,LAST",  # ultimo punto almacenado

                         # "CDEF:Coleccion=cargaCPU,8,*",   #obtiene los octetos de entrada y lo multiplica por 8
                         "CDEF:umbral.15=cargaCPU,.15,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 15
                         "CDEF:umbral.2=cargaCPU,.2,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 2
                         "CDEF:umbral.25=cargaCPU,.25,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 25

                         "AREA:cargaCPU#00FF00:Carga de la RAM",
                         "AREA:umbral.15#CC9900:Carga RAM mayor que 1.5GB",
                         "AREA:umbral.2#FFB74D:Carga RAM mayor que 2GB",
                         "AREA:umbral.25#FF5722:Carga RAM mayor que 2.5GB",

                         "HRULE:.15#CC9900:Umbral 1 - .15%",  # marca de umbral de 1.5
                         "HRULE:.2#FFB74D:Umbral 1 - .2%",  # marca de umbral de 2
                         "HRULE:.25#FF5722:Umbral 1 - .25%",  # marca de umbral de 2

                         "PRINT:cargaLAST:%6.2lf",
                         "GPRINT:cargaMIN:%6.2lf %SMIN",
                         "GPRINT:cargaSTDEV:%6.2lf %SSTDEV",
                         "GPRINT:cargaLAST:%6.2lf %SLAST")
    print(ret)

    ultimo_valor = float(ret['print[0]'])
    if ultimo_valor > 4:
        send_alert_attached("Sobrepasa Umbral línea base", "deteccionRAM.png", comunity, hostname, name)
        print("Sobrepasa Umbral línea base")

def GRAFICAUMBRALSTORAGE(comunity:str, hostname:str, name:str):
    rrdpath = comunity + '_' + hostname + '/'
    imgpath = comunity + '_' + hostname + '/'

    ultima_lectura = int(rrdtool.last(rrdpath + name))
    tiempo_final = ultima_lectura
    tiempo_inicial = tiempo_final - 120

    ret = rrdtool.graphv(imgpath + "deteccionSTORAGE.png",
                         "--start", str(tiempo_inicial),
                         "--end", str(tiempo_final),
                         "--vertical-label=Cpu load",
                         '--lower-limit', '0',
                         '--upper-limit', '8',
                         "--title=Uso de almacenamiento del agente Usando SNMP y RRDtools \n Detección de umbrales",

                         "DEF:cargaCPU=" + rrdpath + "trend3.rrd:CPUload:AVERAGE",
                         # DEF permite generar una variable de tipo colección
                         # VDEF genera un punto con la entrada de una colección
                         "VDEF:cargaMAX=cargaCPU,MAXIMUM",  # el punto maximo
                         "VDEF:cargaMIN=cargaCPU,MINIMUM",  # el punto minimo
                         "VDEF:cargaSTDEV=cargaCPU,STDEV",  # punto de desviación estandar
                         "VDEF:cargaLAST=cargaCPU,LAST",  # ultimo punto almacenado

                         # "CDEF:Coleccion=cargaCPU,8,*",   #obtiene los octetos de entrada y lo multiplica por 8
                         "CDEF:umbral4.5=cargaCPU,4.5,LT,0,cargaCPU,IF",  # CDEF segundo umbral de 2.3

                         "AREA:cargaCPU#00FF00:Carga de Storage",
                         "AREA:umbral4.5#FF9F00:Carga almacenamiento mayor que 4.5",

                         "HRULE:4.5#FF0000:Umbral 1 - 45%",  # marca de umbral de 8

                         "PRINT:cargaLAST:%6.2lf",
                         "GPRINT:cargaMIN:%6.2lf %SMIN",
                         "GPRINT:cargaSTDEV:%6.2lf %SSTDEV",
                         "GPRINT:cargaLAST:%6.2lf %SLAST")
    print(ret)

    ultimo_valor = float(ret['print[0]'])
    if ultimo_valor > 4:
        send_alert_attached("Sobrepasa Umbral línea base", "deteccionSTORAGE.png", comunity, hostname, name)
        print("Sobrepasa Umbral línea base")





mailsender = "martinezescaleradaniel@gmail.com"
mailreceip = "martinezescaleradaniel@gmail.com"
mailserver = 'smtp.gmail.com: 587'
password = 'Martinez97$'

def send_alert_attached(subject, image:str, comunity:str, hostname:str, name:str):
    COMMASPACE = ', '
    # Define params
    rrdpath = comunity + '_' + hostname + '/'
    imgpath = comunity + '_' + hostname + '/'
    fname = name
    """ Envía un correo electrónico adjuntando la imagen en IMG
    """
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = mailsender
    msg['To'] = mailreceip
    fp = open(imgpath + image, 'rb')
    img = MIMEImage(fp.read())
    fp.close()
    msg.attach(img)
    s = smtplib.SMTP(mailserver)

    s.starttls()
    # Login Credentials for sending the mail
    s.login(mailsender, password)

    s.sendmail(mailsender, mailreceip, msg.as_string())
    s.quit()



option = int(input('Bienvenido al gestor de rendimiento de agentes\n'
                      'Puedes escoger la opción que desees\n'
                      '-----------------------------------------\n'
                      '  1.-Agregar agente\n'
                      '  2.-Medir Rendimiento de agente\n'
                      '  0.- Salir\n'))
while option != 0:

    if option == 1:
        r = 's'
        while r == 's':
            print('Para agregar un agente por favor inserte\n----------------')
            print('Nombre de Comunidad')
            comunidad = input()
            print('versión')
            version = input()
            print('Ip del agente')
            ip = input()
            com = consultaSNMP(comunidad, ip, "1.3.6.1.2.1.1.1.0", int(version)-1)
            if com:
                comando = comunidad +' '+ version +' ' + ip
                archivo = open("agentes.txt","a")
                archivo.write(comando+'\n')
                archivo.close
                try:
                    os.mkdir(comunidad + '_' + ip)
                except:
                    pass
                print('Se agrego agente con exito')
            else:
                print('\n\nNo se reconoce el agente\n')
                time.sleep(1)
                print('verifique su creación')
                time.sleep(1)
            print('Quieres agregar otro agente  s/n')
            r = input()
            os.system("clear")


    elif option == 2:
        archivo = open("agentes.txt")
        with open('agentes.txt') as numerolineas:
            lineas = sum(1 for line in numerolineas)
        if lineas < 1:
            print('-------no hay agentes registrados-------')
            time.sleep(3)
            os.system("clear")
        else:
            print('-------Agentes encontrados------\n'+
                  '--------------------------------\n'+
                  '|      Agente     |   Hostname  |\n'+
                  '--------------------------------')
            for i in range(lineas):  # proceso a enlistar los agentes en donde pongo solo la primera palabra de cada linea
                agente = archivo.readline().split()
                print('|' + str(i + 1) + '.-' + agente[0] + '  |' + agente[2] + ' |')

            archivo.close()
            print('---------------------------\n'+
                  '¿Qué agente escoges a monitorizar?')
            resp = input()  # este va a ser la linea donde se selecionará el agente a monitorizar
            archivo = open('agentes.txt')
            agente = archivo.readlines()
            direccion = agente[int(resp)-1].split()

            RDD(direccion[0] + '_' + direccion[2],'trend.rrd')  #se crea la base correspondiente
            RDD(direccion[0] + '_' + direccion[2],'trend2.rrd')
            RDD(direccion[0] + '_' + direccion[2],'trend3.rrd')

            inicio = time.time()           #se establece el tiempo para la monitorizacion
            fin = inicio + 120
            while True:
                print(UPDATERRD(direccion[0],direccion[2],int(direccion[1])-1))
                inicio = time.time()
                if not inicio < fin:
                    break
            GENERARGRAFICAS(direccion[0],direccion[2])
            os.system("clear")

    else:
        print('no se entiende tu respuesta')
        time.sleep(2)
        os.system("clear")

    option = int(input('Bienvenido al gestor de rendimiento de agentes\n'
                       'Puedes escoger la opción que desees\n'
                       '-----------------------------------------\n'
                       '  1.-Agregar agente\n'
                       '  2.-Medir Rendimiento de agente\n'
                       '  0.- Salir\n'))