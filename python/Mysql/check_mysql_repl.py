#!/usr/bin/python
#coding:utf-8
import MySQLdb
import sys
import encrypt
class check_mysql_repl():
    def __init__(self):
        self.conn = MySQLdb.connect(host='127.0.0.1',user='root',passwd=encrypt.decrypt(120,'BAKBLFFDBCLAJAEBJEKELE'),port=33063)
        self.cursor = self.conn.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        self.sql = 'show slave status'
        self.cursor.execute(self.sql)
        self.data = self.cursor.fetchall()
        self.io = self.data[0]['Slave_IO_Running']
        self.sql = self.data[0]['Slave_SQL_Running']
        self.conn.close()
    def get_io_status(self):
        if self.io == 'Yes':
            return 1
        else:
            return 0
	   
    def get_sql_status(self):
        if self.sql == 'Yes':
            return 1
        else:
            return 0
	   
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print"Usage: %s [io|sql]" % sys.argv[0]
        sys.exit(1)
    mysql = check_mysql_repl()
    if sys.argv[1] == "io":
        print mysql.get_io_status()
    elif sys.argv[1] == "sql":
        print mysql.get_sql_status()
