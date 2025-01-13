import MySQLdb
from MySQLdb.cursors import DictCursor
import types
from pprint import pprint

import brdflix
import settings
       
class ConnectionInfo(object):
    def __init__(self, host="", port=3306, user="", password="", db_name=""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name

class MySqlHelper(object):
    def __init__(self, connect_info):
        self._connect_info = connect_info

    def get_generic(self, new_object, row, include_extras=False):
        if row is not None:
            for key, value in row.items():
                if include_extras or key in new_object.__dict__:
                    if isinstance(value, types.StringTypes) and value.startswith("LIST:"):
                        val = value[len("LIST:"):]
                        new_object.__dict__[key] = [ token.strip() for token in val.split(",") ]
                    elif key in new_object.__dict__ and isinstance(new_object.__dict__[key], types.BooleanType):
                        new_object.__dict__[key] = value == 1 or value == True
                    else:
                        new_object.__dict__[key] = value
            return new_object
        else:
            return None

    def delete(self, id_value, id_column, table_name):
        query = "DELETE FROM `{0}` WHERE `{1}` = %s".format(table_name, id_column)
        self.execute(query, (id_value,))

    def delete_generic(self, object):
        query = "DELETE FROM `{0}` WHERE `{1}`=%s".format(object._table_name, object._id_column)
        self.execute(query, (object.get_id(),))

    def insert_or_update_generic(self, object):
        query = "SELECT `{0}` FROM `{1}` WHERE `{0}` = %s".format(object._id_column, object._table_name)
        if self.fetch_one(query, (object.get_id(),)):
            self.update_generic(object)
        else:
            self.insert_generic(object, False)
        
    def insert_generic(self, object, replace_into=False):
        keys = []
        values = []
        columns_str = None
        values_str = None
        for key, value in object.__dict__.items():
            if value is not None and not key in object._ignore_list and not key.startswith('_'):
                keys.append(key)
                if isinstance(value, types.ListType):
                    values.append("LIST:" + ",".join(value))
                else:
                    values.append(value)
                if columns_str:
                    columns_str = "{0},`{1}`".format(columns_str, key)
                else:
                    columns_str = "`{0}`".format(key)
                if values_str:
                    values_str = values_str + ",%s"
                else:
                    values_str = "%s"
        query = "INSERT{0} INTO `{1}` ({2}) VALUES ({3})".format(" OR REPLACE" if replace_into else "", object._table_name, columns_str, values_str)
        res = self.execute(query, values)
        object.set_id(res)
        return res
        
    def update_generic_full(self, object):
        id_value = object.get_id()
        keys = []
        values = []
        set_str = None
        for key, value in object.__dict__.items():
            #TODO: Should 'if value' be there? What if a value was non-null before and we wanted to make it null?
            if value is not None and not key in object._ignore_list and not key.startswith('_'):
                keys.append(key)
                if isinstance(value, types.ListType):
                    values.append("LIST:" + ",".join(value))
                else:
                    values.append(value)
                if set_str:
                    set_str = "{0},`{1}`=%s".format(set_str, key)
                else:
                    set_str = "`{0}`=%s".format(key)
        query = "UPDATE `{0}` SET {1} WHERE `{2}`=%s".format(object._table_name, set_str, object._id_column)
        values.append(id_value)
        return self.execute(query, values)

    def update_generic(self, object, what_list=None):
        if what_list is None:
            return self.update_generic_full(object)
        id_value = object.get_id()
        keys = []
        values = []
        set_str = None
        for key in what_list:
            if key in object.__dict__.keys():
                value = object.__dict__[key]
                if not key in object._ignore_list and not key.startswith('_'):
                    keys.append(key)
                    if isinstance(value, types.ListType):
                        values.append("LIST:" + ",".join(value))
                    else:
                        values.append(value)
                    if set_str:
                        set_str = "{0},`{1}`=%s".format(set_str, key)
                    else:
                        set_str = "`{0}`=%s".format(key)
        query = "UPDATE `{0}` SET {1} WHERE `{2}`=%s".format(object._table_name, set_str, object._id_column)
        values.append(id_value)
        return self.execute(query, values)

    def fetch_one(self, query, values=None):
        cursor, conn = self.create_cursor()
        cursor.execute(query, values)
        one = cursor.fetchone()
        return one

    def fetch_all(self, query, values=None):
        cursor, conn = self.create_cursor()
        cursor.execute(query, values)
        return cursor.fetchall()
        
    def execute(self, query, values=None):
        last_id = None
        cursor, conn = self.create_cursor()
        try:
            cursor.execute(query, values)
        except:
            print 'Error executing on database:'
            print '"{0}"'.format(query)
            print values
        finally:
            last_id = cursor.lastrowid
            conn.commit()
            cursor.close()
        return last_id

    def create_cursor(self):
        s = self._connect_info
        conn = MySQLdb.connect(host=s.host, port=s.port, user=s.user, passwd=s.password, db=s.db_name)
        return (conn.cursor(DictCursor), conn)

    def pretty_print_query(self, query, values=None):
        if values is not None and len(values) > 0:
            #print query % (values)
            print query
        else:
            print query


settings.load_all()
s = settings.MYSQL
DEFAULT = MySqlHelper(ConnectionInfo(s.host, s.port, s.user, s.password, s.db_name if not brdflix.IS_BETA else s.beta_db_name))

        