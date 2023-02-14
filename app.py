# -*- coding: utf-8 -*-


from __future__ import unicode_literals
import requests
import random
import time
import datetime 
from pymongo import MongoClient
from io import StringIO
import calendar
from bs4 import BeautifulSoup
import json



#ref: http://twstock.readthedocs.io/zh_TW/latest/quickstart.html#id2
import twstock

import matplotlib
matplotlib.use('Agg') # ref: https://matplotlib.org/faq/howto_faq.html
import matplotlib.pyplot as plt
import pandas as pd

from imgurpython import ImgurClient

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)

parser= WebhookParser('46c94fddfcdc430174fe74da562a3b0e')

line_bot_api = LineBotApi('7KRObBCLYdqy/6O68ZDZ/UJhauobwFxSc7G4ZDyIPvdts6vLfBUE5Lp6+8SeZP5oKGQRoWCINO/LKCH1Lb2hk/uFXPmncIB7Zm2HTVGVrQNQrYqgK8CSYDRaTtVGwpFFABl4xLfzQQs7FH0Je3bs3wdB04t89/1O/w1cDnyilFU=')






#===================================================
#   stock bot
#===================================================

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        text=event.message.text
        #userId = event['source']['userId']
        if(text.lower()=='me'):
            content = str(event.source.user_id)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        elif(text.lower() == 'profile'):
            profile = line_bot_api.get_profile(event.source.user_id)
            my_status_message = profile.status_message
            if not my_status_message:
                my_status_message = '-'
            line_bot_api.reply_message(event.reply_token, [TextSendMessage(text='Display name: ' + profile.display_name),
                                                           TextSendMessage(text='picture url: ' + profile.picture_url),
                                                           TextSendMessage(text='status_message: ' + my_status_message),]
                                      )

        elif(text.startswith('#')):
            text = text[1:]
            content = ''

            stock_rt = twstock.realtime.get(text)
           

            content += '%s (%s)\n' %(
                stock_rt['info']['name'],
                stock_rt['info']['code'])
            content += '現價: %s / 開盤: %s\n'%(
                stock_rt['realtime']['latest_trade_price'],
                stock_rt['realtime']['open'])
            content += '最高: %s / 最低: %s\n' %(
                stock_rt['realtime']['high'],
                stock_rt['realtime']['low'])
            content += '量: %s\n' %(stock_rt['realtime']['accumulate_trade_volume'])

            stock = twstock.Stock(text)#twstock.Stock('2330')
            content += '-----\n'
            content += '最近五日價格: \n'
            price5 = stock.price[-5:][::-1]
            date5 = stock.date[-5:][::-1]
            for i in range(len(price5)):
                #content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d %H:%M:%S"), price5[i])
                content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d"), price5[i])
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )

        elif(text.startswith('/')):
            text = text[1:]
            fn = '%s.png' %(text)
            stock = twstock.Stock(text)
            my_data = {'close':stock.close, 'date':stock.date, 'open':stock.open}
            df1 = pd.DataFrame.from_dict(my_data)

            df1.plot(x='date', y='close')
            plt.title(' [%s]' %(stock.sid))
            plt.savefig(fn)
            plt.close()

            # -- upload
            # imgur with account: your.mail@gmail.com
            client_id = '5b4d5b8ed2da27f'
            client_secret = '0562eaf3094b75858cd2cdd0ff816b741a19666b'

            client = ImgurClient(client_id, client_secret)
            print("Uploading image... ")
            image = client.upload_from_path(fn, anon=True)
            print("Done")

            url = image['link']
            image_message = ImageSendMessage(
                original_content_url=url,
                preview_image_url=url
            )

            line_bot_api.reply_message(
                event.reply_token,
                image_message
                )
            
        elif(text.startswith('$')):
            text = text[1:]
            content = ''
            yourstock = text
            stock_rt = twstock.realtime.get(text)
            content += '== 股票健檢(技術面和基本面) == \n '
            content += '%s (%s)\n' %(
                stock_rt['info']['name'],
                stock_rt['info']['code'])
            content += '\n'
            today=datetime.datetime.now()
            lastmonth = today - datetime.timedelta(days=31)
            currentdate = datetime.date.today()
            year= currentdate.year
            month = currentdate.month
            day = currentdate.day
            currentday =calendar.weekday(year,month,day)
            loopa=1 
            loopb=2 
            loopc=3
            #------------------------------目前價格----------------------------------
            list_req = requests.get('https://tw.stock.yahoo.com/q/q?s=' + yourstock)
            soup = BeautifulSoup(list_req.content, "html.parser")
            get_stock_price= soup.find(class_='Fz(32px)').text
           #===================================================
           #   技術面
           #===================================================
            content += '技術面數據\n'
            
            avgprice=[]
            list_req = requests.get('http://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG?response=json&date='+today.strftime("%Y%m%d")+'&stockNo='+yourstock) 
            soup = BeautifulSoup(list_req.content, "html.parser") 
            jsonsoup=json.loads(str(soup))
            for i in range(len(jsonsoup['data'])-1):
                avgprice.append(float(jsonsoup['data'][i][1]))
                
            if len(avgprice) < 19:
                list_req = requests.get('http://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG?response=json&date='+ lastmonth.strftime("%Y%m%d")+'&stockNo='+yourstock) 
                soup = BeautifulSoup(list_req.content, "html.parser") 
                jsonsoup=json.loads(str(soup))
                for i in range(len(jsonsoup['data'])-1,1,-1):
                    avgprice.append(float(jsonsoup['data'][i][1]))
                    
            avg2=sum(avgprice[:20])/20
            content +=('20日平均股價：:%s\n' %(avg2))
                
            if  avg2 < float(get_stock_price):
                    content += '該股價高於20日平均\n' 
            elif avg2 == float(get_stock_price):
                    content += '該股價正在20日平均上\n'
            else:
                    content += '該股價在20日平均下\n'
                    
            if len(avgprice) < 4:
                list_req = requests.get('http://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG?response=json&date=' + lastmonth.strftime("%Y%m%d") + '&stockNo=' + yourstock) 
                soup = BeautifulSoup(list_req.content, "html.parser") 
                jsonsoup=json.loads(str(soup))
                for i in range(len(jsonsoup['data'])-1,1,-1):
                    avgprice.append(float(jsonsoup['data'][i][1]))  
                    
            avg=sum(avgprice[:5])/5
            content +=('5日平均股價：:%s\n' %(avg))
                
            if avg < float(get_stock_price):
               content += '該股價高於5日平均\n'
            elif avg == float(get_stock_price):
                content += '該股價正在5日平均上\n'
            else:
                content += '該股價在5日平均之下\n' 
                  
           #===================================================
           #   基本面
           #===================================================
            content += '\n'
            sumstock1=[]
            sumstock2=[]
            sumstock3=[]
            if (currentday==6):
                date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=2),'%Y%m%d')
            elif (currentday==5):
                date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=1),'%Y%m%d')
            else:
                date = datetime.datetime.strftime(datetime.datetime.now(),'%Y%m%d') 
                
            r = requests.get('http://www.twse.com.tw/exchangeReport/BWIBBU_d?response=csv&date=' +date+ '&type=ALL') #先抓一次看有啥鬼 
            if r.text != '\r\n':   #不等於空幹的話
                    get = pd.read_csv(StringIO(r.text), header=1).dropna(how='all', axis=1).dropna(how='any') 
                    get=get[get['證券代號']==yourstock] 
                    if len(get) >0:
                        if get['本益比'].values[0]!='-':
                           get['本益比'] = get['本益比'].str.replace(',','').astype(float) 
                           sumstock1.append(get['本益比'].values[0])
                        else:
                            sumstock1='證交所沒有資料'
                        if get['股價淨值比'].values[0]!='-':
                           get['股價淨值比'] = get['股價淨值比'].astype(float) 
                           sumstock2.append(get['股價淨值比'].values[0])
                        else:
                           sumstock2='證交所沒有資料'            
                        if get['殖利率(%)'].values[0]!='-':
                           get['殖利率(%)'] = get['殖利率(%)'].astype(float) 
                           sumstock3.append(get['殖利率(%)'].values[0])
                        else:
                           sumstock3='證交所沒有資料'
            elif r.text == '\r\n':      #等於空幹的話
                    if (currentday==0):
                        date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=3),'%Y%m%d')
                    else:
                        date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=1),'%Y%m%d')
                        
                    r = requests.get('http://www.twse.com.tw/exchangeReport/BWIBBU_d?response=csv&date=' +date+ '&type=ALL')
                    get = pd.read_csv(StringIO(r.text), header=1).dropna(how='all', axis=1).dropna(how='any')
                    get=get[get['證券代號']==yourstock] 
                    
                    if len(get) >0:
                        if get['本益比'].values[0]!='-':
                            get['本益比'] = get['本益比'].str.replace(',','').astype(float) 
                            sumstock1.append(get['本益比'].values[0])
                        else:
                            sumstock1='證交所沒有資料'
                
                        if get['股價淨值比'].values[0]!='-':
                            get['股價淨值比'] = get['股價淨值比'].astype(float) 
                            sumstock2.append(get['股價淨值比'].values[0])
                        else:
                            sumstock2='證交所沒有資料'
                        if get['殖利率(%)'].values[0]!='-':
                            get['殖利率(%)'] = get['殖利率(%)'].astype(float) 
                            sumstock3.append(get['殖利率(%)'].values[0])
                        else:
                            sumstock3='證交所沒有資料'
                            
            content += '基本面數據\n'     
            content +=('本益比：:%s\n' %(sumstock1))
            content +=('股價淨值比：:%s\n' %(sumstock2))
            content +=('殖利率：:%s\n' %(sumstock3))
            content += '\n'
           #===================================================
           #   分析
           #===================================================
            content += ' == 技術面分析判斷 ==\n'
            if avg<float(get_stock_price) and avg2<float(get_stock_price) and avg>avg2:
               content += '覺得趨勢很可以\n\n'
            elif avg<float(get_stock_price) and avg2<float(get_stock_price):
               content += '覺得趨勢還行\n\n'
            else:
               content += '覺得趨勢不太行\n\n'
                
            content += ' == 基本面分析判斷 ==\n'
            if  sumstock1!='垃圾證交所沒有東西' and sumstock2!='垃圾證交所沒有東西' and sumstock3!='垃圾證交所沒有東西':
               if get['本益比'].values[0]<13 and get['本益比'].values[0]>5 and get['股價淨值比'].values[0]<0.7 and get['殖利率(%)'].values[0]>1.4:
                    if get['殖利率(%)'].values[0]>5:
                           content += '覺得趨勢很棒\n\n'
                    else:
                         content += '覺得趨勢還行\n\n'
                            
               elif get['本益比'].values[0]<30 and get['本益比'].values[0]>5 and get['殖利率(%)'].values[0]>1.4:
                    if get['股價淨值比'].values[0]>1:
                        if get['殖利率(%)'].values[0]>5:
                           content += '難達到5%以上的報酬率且股價較高,但還趨勢不錯\n\n'
                        else:
                            content += '難達到5%以上的報酬率且股價較高,但趨勢不錯,看看口袋資金吧\n\n'
                    elif get['股價淨值比'].values[0]<1:
                        if get['殖利率(%)'].values[0]>5:
                           content += '難達到5%以上的報酬率但股價低,但趨勢還不錯\n\n'
                        else:
                            content += '難達到5%以上的報酬率但股價低,再想想好了\n\n'
                    else:
                         content += '覺得還行\n\n'
                            
               elif get['本益比'].values[0]>40 :
                         content += '股價可能在被高估的狀態\n\n'
                    
               elif get['殖利率(%)'].values[0]<1.4:
                         content += '股價殖利率低於市場利率,不想分析\n\n'
               else:
                    content += '覺得趨勢不太行\n\n'
            else:
                 content += '沒有數值無法分析\n\n'
           
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=content))
            
        elif(text.startswith('&')):
            text = text[1:]
            content = ''
            yourstock = text
            stock_rt = twstock.realtime.get(text)
            content += '=股票健檢(籌碼面和四大買賣點)= \n '
            content += '%s (%s)\n' %(
                stock_rt['info']['name'],
                stock_rt['info']['code'])
            content += '\n'
           #===================================================
           #   籌碼面
           #===================================================
            sumstock=[]
            for i in range(7,0,-1):
                date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=i),'%Y%m%d') 
                r = requests.get('http://www.tse.com.tw/trading/fund/T86?response=csv&date='+date+'&selectType=ALLBUT0999') 
                if r.text != '\r\n': 
                    get = pd.read_csv(StringIO(r.text), header=1).dropna(how='all', axis=1).dropna(how='any') 
                    get=get[get['證券代號']==yourstock] 
                    if len(get) >0:
                        get['三大法人買賣超股數'] = get['三大法人買賣超股數'].str.replace(',','').astype(float) 
                        if get['三大法人買賣超股數'].values[0] >0:
                            sumstock.append('買')
                        else:
                            sumstock.append('賣')
            content += '籌碼面數據\n'     
            content +=('三大法人買賣狀況（一周近況):\n%s\n' %(sumstock))
            
            a=[]
            content += '\n'
            content += ' == 籌碼面分析判斷 ==\n'
            sumstock.reverse()
            if sumstock[0]==sumstock[1]=='買' or sumstock[0]=='\r\n' or sumstock[1]=='\r\n':
                if sumstock[2]==sumstock[3]==sumstock[4]=='買':
                    content += '5連買需需觀察,搭配其他指標觀察一下趨勢吧\n\n'
                elif sumstock[2]==sumstock[3]=='買':
                    content += '4連買趨勢有點香啊\n\n'
                elif sumstock[2]=='買':
                    content += '3連買的趨勢可以考慮\n\n'
                else:
                    content += '2連買趨勢覺得可以考慮\n\n'
            elif sumstock[0]==sumstock[1]=='賣':
                if sumstock[2]==sumstock[3]==sumstock[4]=='賣':
                    content += '5連賣需觀察,搭配其他指標觀察一下趨勢吧\n\n'
                elif sumstock[2]==sumstock[3]=='賣':
                    content += '4連賣真的危險啊\n\n'
                elif sumstock[2]=='賣':
                    content += '3連賣太危險,飛太遠\n\n'
                else:
                    content += '2連賣覺得略危險\n\n'
            else:
                content += '局勢不太明顯,需要再觀察\n\n'
            stock = twstock.Stock(text)
            bfp = twstock.BestFourPoint(stock)
            a=bfp.best_four_point()             # 綜合判斷
            content += ' == 四大買賣點判斷 ==\n'
            if a[0]==False:
                content += '建議可以放空或是賣,因為:\n'
            else:
                content += '建議可以做空或是買,因為:\n'
            content += '%s' %(a[1])
            if a[1]=='量縮價不跌, 三日均價大於六日均價':
                content += ',且有兩個訊號趨勢呈現好\n\n'
            elif a[1]=='三日均價大於六日均價':
                content += ',但只有一個訊號趨勢呈現好\n\n'
                
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=content))
            
        elif(text.startswith('%')):
            text = text[1:]
            content = ''
            yourstock = text
            stock_rt = twstock.realtime.get(text)
            list_req = 'https://tw.finance.yahoo.com/news_search.html?ei=Big5&q=' +yourstock
            content += '%s (%s)' %(
                stock_rt['info']['name'],
                stock_rt['info']['code'])
            content += '   相關新聞\n'
            content += '%s'%(list_req) 
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
            
        elif(text.startswith('hi') or text.startswith('HI') or text.startswith('Hi') or text.startswith('hI')):
            content = ''
            content += '指令表(例如:#2330)\n'
            content += '# 股票號碼:顯示股票價格\n'
            content += '/ 股票號碼:顯示股票價格圖表\n'
            content += '$ 股票號碼:股票健檢(技術面和基本面)\n'
            content += '& 股票號碼:股票健檢(籌碼面和四大買賣點)\n'
            content += '% 股票號碼:股票相關新聞\n'
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
            
    return 'OK'


@app.route("/", methods=['GET'])
def basic_url():
    return 'OK'

import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
