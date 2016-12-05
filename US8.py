import sqlite3
import time
import datetime
import random
import smtplib

conn = sqlite3.connect('Parent.db')
c = conn.cursor()

def create_table():
    c.execute("CREATE TABLE IF NOT EXISTS ParentAccount(ParentFirstName Text,ParentLastName,unix REAL, datestamp TEXT, keyword TEXT, value REAL)")


def data_entry():
    c.execute("INSERT INTO ParentAccount VALUES(badr,alotaibi,1452549219,'2016-01-11 13:53:39','parent',6)")
    
    conn.commit()
    c.close()
    conn.close()

def dynamic_data_entry():

    unix = int(time.time())
    date = str(datetime.datetime.fromtimestamp(unix).strftime('%Y-%m-%d %H:%M:%S'))
    keyword = 'Parent'
    value = random.randrange(0,20)
    ParentFirstName = 'badr'
    ParentLastName = 'Alotaibi'
    c.execute("INSERT INTO ParentAccount(unix, datestamp, keyword, value,ParentFirstName,ParentLastName) VALUES (?, ?, ?, ?, ?, ?)",
          (unix, date, keyword, value, ParentFirstName,ParentLastName))

    conn.commit()
    time.sleep(1)

def read_from_db():
    c.execute('SELECT * FROM ParentAccount')
    data = c.fetchall()
    print(data)
    for row in data:
        print(row)

    c.execute('SELECT * FROM ParentAccount WHERE ParentFirstName = badr')
    data = c.fetchall()
    print(data)
    for row in data:
        print(row)
    
read_from_db()
c.close
conn.close()

content = 'congratulations you have created your account successfully'

mail = smtplib.SMTP('smtp.gmail.com',587)

mail.ehlo()

mail.startls()

mail.login('email','password')

mail.sendmail('fromemail','reciver',you created your account succuflly)

mail.close()

