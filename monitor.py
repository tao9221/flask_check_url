#/usr/bin/env python
#coning=utf-8

import sys
import MySQLdb
import commands
import datetime, time
import threading


def Monitor(item, ip, url):
    surl=url.replace('\r\n','')
    surl=url.replace('\n','')
    surl=url.replace('\r','')
    TimeNow=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if ':' in ip:
        Result=commands.getoutput('/usr/bin/curl -m 10 -o /dev/null -x '+ip.strip()+' -s -w "%{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{size_download}" "'+surl +'"')
    else:
        Result=commands.getoutput('/usr/bin/curl -m 10 -o /dev/null -x '+ip.strip()+':80 -s -w "%{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{size_download}" "'+surl+'"')
    with open("/root/monitor.log",'a') as f:
        f.write(TimeNow + " - "+item+" "+ip+" "+url.replace('\n','')+" "+Result+"\n")

#########data from db###
cdb=MySQLdb.connect(host='127.0.0.1',user='root',passwd='root')
cdb.select_db('weburl')
cursor=cdb.cursor()
cursor.execute('select url_id,ip,url,remark,item from itemsurl, items where itemsurl.items_id=items.items_id;')
data=cursor.fetchall()
itemurl = [row for row in data]

#with open("/root/myproject/monitorfile") as f:
#    numurl=len(f.readlines())

#with open("/root/myproject/monitorfile") as f:
#    for url in range(0,numurl):
#########threads run
if len(itemurl)>0:
    threads=[]
    for urls in itemurl:
        t = threading.Thread(target=Monitor, args=(urls[4], urls[1], urls[2]))
        threads.append(t)

if __name__=='__main__':
    for t in threads:
        t.setDaemon(True)
        if threads[len(threads)-1]==t:
            time.sleep(0.5)
            t.start()
        else:
            t.start()
#        t.start()
    t.join()
    while True:
        ps_zi=commands.getoutput('ps aux|grep "http_code"|grep -v "grep"')
        if len(ps_zi):
            time.sleep(0.5)
        else:
            break
with open("/root/monitor.log",'a') as f:
    f.write("--time---"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"---all over--\n")
