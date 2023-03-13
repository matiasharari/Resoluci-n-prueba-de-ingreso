# -*- coding: utf-8 -*-
"""
Created on Sun Mar 12 16:56:51 2023

@author: matia
"""

import pyRofex
import yfinance as yf
import numpy as np
import pandas as pd


#Set the parameter for the REMARKET environment
#Seteo los parametros para conectar con la API

pyRofex.initialize(user="matiasharari20017855",
                   password="iodozJ9%",
                   account="REM7855",
                  environment=pyRofex.Environment.REMARKET)

# Uses the MarketDataEntry enum to define the entries we want to subscribe to
#Seteo los datos que quiero extraer
entries = [pyRofex.MarketDataEntry.BIDS,
           pyRofex.MarketDataEntry.OFFERS]




#Creo una lista por activo especificado en la consigna. La idea es poder buscar dentro de la base
# de datos todos los contratos que aparezcan para cada uno de estos activos en particular.
lista_YPF=[]
lista_GGAL = []
lista_PAM = []
lista_DLR = []
data = pyRofex.get_all_instruments()
data = data["instruments"]
for dic in data :
    palabra=dic["instrumentId"]["symbol"]
    if "YPFD"in palabra[:5]:
        lista_YPF.append(palabra)
    elif "GGAL" in palabra[:5]:
        lista_GGAL.append(palabra)
    elif "PAMP" in palabra[:5]:
        lista_PAM.append(palabra)
    elif "DLR" in palabra[:5]:
        lista_DLR.append(palabra)
        
lista_contratos = lista_YPF + lista_GGAL + lista_PAM
lista_contratos.append('DLR/NOV23')

#Armo un Dataframe con todos los contratos de acciones especificadas y un contrato de dolar. Solo estan los tickers por ahora.
data = pd.DataFrame(lista_contratos)

data = data.rename(columns ={0 : 'Contratos'})

#Defino una funcion que extraiga la informacion necesaria de la API de Rofex(Bid y Offer) y que lo guarde en su respectiva lista para luego agregarlas como columnas al dataframe.
def precios(contratos):
    df = np.zeros((len(contratos),2))
    df = pd.DataFrame(df)
    df = df.rename(columns = {0:'BID',1:'OFFER'})
    lista_bid = []
    lista_offer = []
    for i in range(len(contratos)):
        contrato = contratos[i]
        market_data = pyRofex.get_market_data(ticker=contrato,
                            entries=entries)["marketData"]
        if not market_data["BI"] and not market_data["OF"]:
            lista_bid.append(0)
            lista_offer.append(0)
        else:
            if len( market_data["BI"])==0:
                lista_bid.append(0)
            else:
                lista_bid.append(market_data["BI"][0]["price"])
            if len(market_data["OF"])==0:
                lista_offer.append(0)
            else:
                lista_offer.append(market_data["OF"][0]["price"])
    df['BID'] = lista_bid
    df['OFFER'] = lista_offer
        
    return df
         
activos = precios(lista_contratos)

data['BID'] = activos['BID']
data['OFFER'] = activos['OFFER']
data.drop(data[data['Contratos'].str.len() > 10].index, inplace=True)
#Tengo un ticker que no es contrato accion/ABR23/JUN23, los borro del df.

#Defino una funcion que me traiga los precios de los activos subyacentews extraidos de Yahoo Finance.
def precios_st(tickers):
    dic = {}
    for ticker in tickers:        
        tickerSymbol = ticker
        tickerData = yf.Ticker(tickerSymbol)
        tickerPrice = tickerData.history(period='1d')['Close'][0]
        dic [ticker]= tickerPrice
    return dic
   
#Como borre filas del dataframe, vuelvo a generar el indice para que me quede completo y ordenado.
data.index = range(0, len(data))

#Uso el loop para generar los tickers de los activos.
lista_stocks = []
for i in data.index:
    if len(data.loc[i,'Contratos'])>9:
        symbol = data.loc[i, 'Contratos'][:4]
        if symbol == 'YPFD' or symbol == 'GGAL' or symbol == 'PAMP':
            symbol += '.BA'
    else: 
        symbol = data.loc[i,'Contratos'][:3]
        if symbol == 'DLR':
            symbol = 'ARS=X'
    lista_stocks.append(symbol)
            
data['Stock'] = lista_stocks


#Extraigo los tickers de los activos del dataframe
activos = data["Stock"].unique()

#Uso la función de precios para generarme un diccionario con los activos como valor y los precios como claves.
precios_dict = precios_st(activos)

#Me genero una columna de precios en el dataframe
data['Precios'] = np.nan

#Completo la columna con los precios de los activos
for i in data.index:
    stock_symbol = lista_stocks[i]
    if stock_symbol in precios_dict:
        data.loc[i, 'Precios'] = precios_dict[stock_symbol]
        


#Calculo tasas colocadoras(Fbid/St) y tomadoras implicitas(Foffer/St)       
data['Tasa Tomadora'] = (data['BID']/data['Precios'])-1
data['Tasa Colocadora'] = data['OFFER']/data['Precios']-1

data = data.replace(-1, np.nan)


#Anualizo las tasas

#Completo una nueva columna con el mes de vencimiento
lista_mes = []
for index, row in data.iterrows():
    contrato = row['Contratos']
    if len(contrato)>9:
        mes = contrato[5:8]
    else:
        mes = contrato[4:7]

    if mes == 'FEB':
        mes = 2
    elif mes == 'ABR':
        mes = 4
    elif mes == 'JUN':
        mes = 6
    elif mes == 'AGO':
        mes = 8
    elif mes == 'OCT':
        mes = 10
    elif mes == 'NOV':
        mes = 11
    elif mes == 'DIC':
        mes = 12
    lista_mes.append(mes)

data['Mes Vencimiento'] = lista_mes

#Busco la fecha de vencimiento que es el ultimo dia habil del mes
from pandas.tseries.offsets import BMonthEnd


fecha_vencimiento = []
for index, row in data.iterrows():
    vencimiento = row['Mes Vencimiento']
    year = 2023
    last_business_day = pd.Timestamp(year=year, month=vencimiento, day=1) + BMonthEnd()
    fecha_vencimiento.append(last_business_day)
    
data['Fecha Vencimiento'] = fecha_vencimiento

#Calculo los dias al vencimiento como la di
from datetime import datetime
today = datetime.today()

difference_in_days = (data['Fecha Vencimiento'].apply(lambda x: x - today)).dt.days

data['Dias_vencimiento'] = difference_in_days

data['Tasa Colocadora'] = (1+data['Tasa Colocadora'])**(360/data['Dias_vencimiento'])-1
data['Tasa Tomadora'] = (1+data['Tasa Tomadora'])**(360/data['Dias_vencimiento'])-1

        
#Comparo las tasas implicitas entre los distintos contratos y busco colocadora > tomadora. En esos casos hay arbitraje.

lista_arbitraje_activo1 = []
lista_colocadora_1 = []
lista_tomadora_1 = []
lista_colocadora_2 = []
lista_tomadora_2 = []
lista_arbitraje_activo2 = []
lista_arbitraje = []

for i in range(len(data)):
    activo1 = data.loc[i,'Contratos']
    dias_1 = data.loc[i,'Dias_vencimiento']
    colocadora_1 = data.loc[i,'Tasa Colocadora']
    tomadora_1 = data.loc[i,'Tasa Tomadora']
    for j in range(len(data)):
        activo2 = data.loc[j,'Contratos']
        dias_2 = data.loc[j,'Dias_vencimiento']
        colocadora_2 = data.loc[j,'Tasa Colocadora']
        tomadora_2 = data.loc[j,'Tasa Tomadora']
        if dias_1 == dias_2:
            if activo1 != activo2:
                if colocadora_1 > tomadora_2 or colocadora_2 > tomadora_1:
                    lista_arbitraje.append('Hay arbitraje')
                    lista_arbitraje_activo1.append(activo1)
                    lista_arbitraje_activo2.append(activo2)    
                    lista_colocadora_1.append(colocadora_1)
                    lista_tomadora_1.append(tomadora_1)
                    lista_colocadora_2.append(colocadora_2)
                    lista_tomadora_2.append(tomadora_2)
                    
                    

data_arbitraje = pd.DataFrame(lista_arbitraje_activo1)
data_arbitraje = data_arbitraje.rename(columns ={0 : 'Activo 1'})
data_arbitraje['Activo 2'] = lista_arbitraje_activo2
data_arbitraje['Arbitraje'] = lista_arbitraje
data_arbitraje['Colocadora 1'] = lista_colocadora_1
data_arbitraje['Tomadora 1'] = lista_tomadora_1
data_arbitraje['Colocadora 2'] = lista_colocadora_2
data_arbitraje['Tomadora 2'] = lista_tomadora_2

data_arbitraje = data_arbitraje.drop_duplicates(subset=["Activo 2"]) 





#Trate de hacerlo ayudandome de ChatGPT pero tampoco pude, la funcion de get_message no funciona mas en pyRofex
# Defino market data handler para quedarme con los datos de los mensajes
def market_data_handler(message):
    ticker = message["instrumentId"]["symbol"]
    bid_price = message["marketData"]["BI"][0]["price"]
    ask_price = message["marketData"]["OF"][0]["price"]
    last_price = message["marketData"]["LA"]["price"]
    return ticker, bid_price, ask_price

#Defino una función para poder actualizar el dataframe con los nuevos datos
def update_market_data(data, ticker, bid_price, ask_price):
    data.loc[data['Contratos'] == ticker, 'BID'] = bid_price
    data.loc[data['Contratos'] == ticker, 'ASK'] = ask_price
    return data

# Initiate Websocket Connection
pyRofex.init_websocket_connection(market_data_handler=market_data_handler)

# Instruments list to subscribe
instruments = data['Contratos']


# Subscribes to receive market data messages
pyRofex.market_data_subscription(tickers=instruments,
                                 entries=entries)

# Loop to continuously update the data DataFrame
while True:
    try:
        # Wait for a message to be received
        message = pyRofex.wait_websocket_message()
        # Handle the message using the market_data_h
        # Handle the message using the market_data_handler function
        ticker, bid_price, ask_price = market_data_handler(message)
        # Update the data DataFrame with the new market data
        data = update_market_data(data, ticker, bid_price, ask_price)
    except KeyboardInterrupt:
        # Stop the loop when the user presses Ctrl+C
        break

# Close the websocket connection
pyRofex.close_websocket_connection()


