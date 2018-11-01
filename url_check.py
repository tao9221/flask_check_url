#!/usr/bin/python env
#coding:utf-8

import os,sys
import MySQLdb
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
reload(sys)
sys.setdefaultencoding('utf-8')
SECRET_KEY='development key'
########monitor.py import#####
import sys
import commands
import datetime, time
import threading
########monitor import end####

app=Flask(__name__)
app.config.from_object(__name__)

########monitor.py###########
def Monitor(item, ip, url):
    TimeNow=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    surl=url.replace('\r\n','')
    surl=url.replace('\n','')
    surl=url.replace('\r','')
    if ':' in ip:
        Result=commands.getoutput('/usr/bin/curl -m 10 -o /dev/null -x '+ip.strip()+' -s -w "%{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{size_download}" "'+surl.strip()+'"')
    else:
        Result=commands.getoutput('/usr/bin/curl -m 10 -o /dev/null -x '+ip.strip()+':80 -s -w "%{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{size_download}" "'+surl.strip()+'"')
    reports.append(TimeNow + ' - '+item+' '+ip+' '+surl+' | '+Result+'\n')
    #reports.append(TimeNow + ' - '+item+' '+ip+' '+surl+' '+Result+'\n')
    with open("/root/monitor.log",'a') as f:
        f.write(TimeNow + " - "+item+" "+ip+" "+surl+" "+Result+"\n")
    
########monitor.py end#######
def conect_db():
    global cdb
    cdb=MySQLdb.connect(host='127.0.0.1',user='root',passwd='root')
    cdb.select_db('weburl')
    global cursor
    cursor=cdb.cursor()
    
def datas_items():
    if session.get('userid')==1:
        cursor.execute('select url_id,ip,url,remark,item from itemsurl, items where itemsurl.items_id=items.items_id;')
        data=cursor.fetchall()
        cursor.execute('select * from items;')
        datas=cursor.fetchall()
    else:
        item_n=session.get('item')
        sl=["itemsurl.items_id=items.items_id and itemsurl.items_id="+x for x in ''.join(list(item_n)) if x!=',']
        cursor.execute('select url_id,ip,url,remark,item from itemsurl, items where %s;' %(' or '.join(sl)))
        data=cursor.fetchall()
        cursor.execute('select * from items where items_id=%s;' %(' or items_id='.join(item_n.split(','))))
        datas=cursor.fetchall()
    global itemurl
    itemurl=[dict(id=row[0], ip=row[1], url=row[2], remark=row[3], item=row[4]) for row in data]
    global items
    items=[dict(ids=row[0], item=row[1]) for row in datas]

@app.before_request
def befor_request():
    conect_db()

@app.after_request
def after_request(response):
    cdb.close()
    return response
@app.route('/')
def show_index():
    if session.get('logged_in'):
        return redirect(url_for('check_index'))
    else:
        return redirect(url_for('login'))

@app.route('/checkindex', methods=['GET'])
def check_index():
    if session.get('logged_in'):
        datas_items()
        return render_template('check_index.html',items=items) 
@app.route('/showcheck', methods=['POST'])
def show_check():
    if session.get('logged_in'):
        item_name=request.form['item_only']
        cursor.execute('select url_id,ip,url,remark,item from itemsurl, items where itemsurl.items_id=items.items_id and itemsurl.items_id="%s";' %(item_name))
        data=cursor.fetchall()
        itemurl = [row for row in data]
        if len(itemurl)>0:
            global reports
            reports=[]
            threads=[]
            for urls in itemurl:
                t = threading.Thread(target=Monitor, args=(urls[4], urls[1], urls[2]))
                threads.append(t)
            for t in threads:
                t.setDaemon(True)
                if threads[len(threads)-1]==t:
                    time.sleep(0.5)
                    t.start()
                else:
                    t.start()
            t.join()
            while True:
                ps_zi=commands.getoutput('ps aux|grep "http_code"|grep -v "grep"')
                if len(ps_zi):
                    time.sleep(1)
                else:
                    break
            #time.sleep(10) 
            with open("/root/monitor.log",'a') as f:
                f.write("--time---"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"---web check over--\n")
            datas_items()
            #return render_template('url.html',items=reports)
            return render_template('check_index.html',itemurl=reports ,items=items)
        else:
           flash('item check url null')
           return redirect(url_for('check_index'))
    else:
        return redirect(url_for('check_index'))

@app.route('/showurl')
def show_url():
    if session.get('logged_in'):
        datas_items()
        return render_template('show_url.html', itemurl=itemurl, items=items)
    else:
        return redirect(url_for('add_entry')) 

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    item_name=request.form['item_only']
    iplist=request.form['iplist'].split('\r\n')
    checkurl=request.form['urllist'].split('\r\n')
    #return render_template('url.html',items=checkurl)
    if len(iplist) < 1:
        flash('iplist is null')
        return redirect(url_for('show_url'))
    elif len(checkurl) < 1:
        flash('checkurl is null')
        return redirect(url_for('show_url'))
    else:
        for ip in iplist:
            for url in checkurl:
                cursor.execute('insert into itemsurl (items_id, ip, url) value("%s","%s","%s");' %(item_name,ip,url))
                flash(item_name + ' ' + ip + ' ' + url + 'add successfully')
                cdb.commit()
    return redirect(url_for('show_url'))

@app.route('/search', methods=['POST'])
def search_url():
    if not session.get('logged_in'):
        abort(401)
    search=request.form['sch']
    item_n=session.get('item')
    if session.get('userid')==1:
        rr=['ip','url','remark']
        lsl=[x+" like '%"+search+"%'" for x in rr]
        cursor.execute('select url_id,ip,url,remark,item from itemsurl, items where (itemsurl.items_id=items.items_id) and (%s);' %(' or '.join(lsl)))
        data=cursor.fetchall()
        itemurl = [dict(id=row[0], ip=row[1], url=row[2], remark=row[3], item=row[4]) for row in data]
        cursor.execute('select * from items')
        datas=cursor.fetchall()
        items = [dict(ids=row[0], item=row[1]) for row in datas]
    else:
        rr=['ip','url','remark']
        sl=["itemsurl.items_id=items.items_id and itemsurl.items_id="+x for x in ''.join(list(item_n)) if x!=',']
        lsl=[x+" like '%"+search+"%'" for x in rr]
        cursor.execute('select url_id,ip,url,remark,item from itemsurl, items where (itemsurl.items_id=items.items_id) and (%s) and (%s);' %(' or '.join(sl),' or '.join(lsl) ))
        data=cursor.fetchall()
        itemurl = [dict(id=row[0], ip=row[1], url=row[2], remark=row[3], item=row[4]) for row in data]

        itemsl=["items_id="+x for x in ''.join(list(item_n)) if x!=',']
        cursor.execute('select * from items where %s;' %(' or '.join(itemsl)))
        datas=cursor.fetchall()
        items = [dict(ids=row[0], item=row[1]) for row in datas]
    return render_template('show_url.html', itemurl=itemurl, items=items)

@app.route('/del', methods=['GET','POST'])
def del_entry():
    if not session.get('logged_in'):
        abort(401)
    if request.form["anniu"] == "Delete":
       cursor.execute('delete from itemsurl where url_id="%s";' %(request.form['id']))
       cdb.commit()
       flash(request.form['ip'] + ' ' + request.form['url'] + ' del successfully')
    elif request.form["anniu"] == "Update":
       cursor.execute('update itemsurl set ip="%s",url="%s",remark="%s" where url_id="%s";' %(request.form['ip'],request.form['url'],request.form['remark'],request.form['id']))
       cdb.commit()
       flash(request.form.get('ip') + ' ' + request.form['url'] + ' update successfully')
    return redirect(url_for('show_url'))

###add user####
@app.route('/adduser', methods=['GET','POST'])
def add_user():
    if session.get('logged_in') and session.get('userid')==1:
        cursor.execute('select * from items;')
        data=cursor.fetchall()
        items = [dict(ids=row[0], item=row[1]) for row in data]
        return render_template('add_user.html', items=items, uid=session.get('userid'))
    else:
        flash('name must admin,please connect admin user!')
        return redirect(url_for('login'))
@app.route('/addu', methods=['POST'])
def add_u():
    if session.get('logged_in') and session.get('userid')==1:
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        ck=request.form.getlist('item')
        if request.form['userniu']=='Adduser':
            if not username:
               flash(username + ' not null!')
               return redirect(url_for('add_user'))
            else:
               cursor.execute('select name from items_user where name="%s";' %(username))
               data=cursor.fetchone()
               if data:
                   flash(username + ' is in name list!')
                   return redirect(url_for('add_user'))
            if not password or len(password) < 5:
               flash('password not <5 or not null!')
               return redirect(url_for('add_user'))
            elif not email or len(email.split('@'))!=2:
               flash('email split not with @ or not null!')
               return redirect(url_for('add_user'))
            elif not ck:
               flash('item not null!')
               return redirect(url_for('add_user'))
            if len(ck) > 1:    
                cursor.execute('insert into items_user (name,password,email,item) value("%s","%s","%s","%s");' %(username,password,email,','.join(ck)))
            else:
                cursor.execute('insert into items_user (name,password,email,item) value("%s","%s","%s","%s");' %(username,password,email,''.join(ck)))
            cdb.commit()
            flash(username + ' add successfully')
            return redirect(url_for('login'))
        elif request.form['userniu']=='Upduser':
            if not username:
               flash(username + ' not null!')
               return redirect(url_for('add_user'))
            else:
               cursor.execute('select name from items_user where name="%s";' %(username))
               data=cursor.fetchone()
               if not data:
                   flash(username + ' not in name list!')
                   return redirect(url_for('add_user'))
            if not password or len(password) < 5:
               flash('password not <5 or not null!')
               return redirect(url_for('add_user'))
            elif not email or len(email.split('@'))!=2:
               flash('email split not with @ or not null!')
               return redirect(url_for('add_user'))
            elif not ck:
               flash('item not null!')
               return redirect(url_for('add_user'))
            if len(ck) > 1:
                cursor.execute('update items_user set password="%s",email="%s",item="%s" where name="%s";' %(password,email,','.join(ck),username))
            else:
                cursor.execute('update items_user set password="%s",email="%s",item="%s" where name="%s";;' %(password,email,''.join(ck),username))
            cdb.commit()
            flash(username + ' update successfully')
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

####login logout control
@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        cursor.execute('select name,password,user_id,item from items_user where name="%s"' %request.form['username'])
        np=cursor.fetchone()
        if np:
            if request.form['username'] != np[0]:
                error='Invalid username'
            elif request.form['password'] != np[1]:
                error='Invalid password'
            else:
                session['logged_in']=True
                session['name']=np[0]
                session['userid']=np[2]
                session['item']=np[3]
                flash('You logged in')
                return redirect(url_for('show_index'))
        else:
            error='Invalid username'
    return render_template('login.html',error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in',None)
    session.pop('userid',None)
    session.pop('name',None)
    flash('You logged out')
    return redirect(url_for('login'))
####login end#####

####item add, delete ,update####
@app.route('/show_item')
def show_item():
    if session.get('logged_in') and session.get('userid')==1:
        cursor.execute('select * from items;')
        data=cursor.fetchall()
        items = [dict(ids=row[0], item=row[1]) for row in data]
        return render_template('show_item.html', items=items)
    else:
        flash('name must admin,please connect admin user!')
        return redirect(url_for('login'))

@app.route('/additem',methods=['POST'])
def add_item():
    if not session.get('logged_in'):
        abort(401)
    cursor.execute('insert into items (item) values ("%s");' %(request.form['item']))
    cdb.commit()
    flash(request.form['item'] + ' add successfully')
    return redirect(url_for('show_item'))

@app.route('/delitem',methods=['POST'])
def del_item():
    if not session.get('logged_in'):
       abort(401)
    if request.form["anniu"] == "Delete":
       cursor.execute('delete from items where items_id="%s";' %(request.form['item_ids']))
       cdb.commit()
       flash(request.form['item_zhi'] + ' del successfully')
    elif request.form["anniu"] == "Update":
       cursor.execute('update items set item="%s" where items_id="%s";' %(request.form['item_zhi'],request.form['item_ids']))
       cdb.commit()
       flash(request.form.get('item_zhi') + ' update successfully')
    return redirect(url_for('show_item'))
####item end####

if __name__=='__main__':
    #app.run(host='0.0.0.0',debug=True)
    app.run(host='0.0.0.0')
