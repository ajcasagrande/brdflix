import sqlite3
import types
import brdflix

class TableMetadata:
    def __init__(self):
        self.id_column = "id"
        self.table_name = None
        self.ignore_list = []
        
    def get_id(self, object):
        return object.__dict__[self.id_column]

'''
Retreives the single item from the database that matches this id
'''
def get_single(new_object, id):
    row = db_fetch_one(brdflix.DATABASE_FILENAME, "SELECT * FROM {0} WHERE id = ?".format(table_name), [id])
    return get_generic(new_object, row, False) if row else None

'''
Retreives all items in the database from given table, casted to type
'''
def get_all(object_type, table_name):
    rows = db_fetch_all(brdflix.DATABASE_FILENAME, "SELECT * FROM {0}".format(table_name))
    return [ get_generic(object_type(), row, False) for row in rows ]
        
def get_generic(new_object, row, include_extras=False):
    if row:
        for index, value in enumerate(row):
            key = row.keys()[index]
            if include_extras or key in new_object.__dict__:
                if isinstance(value, types.StringTypes) and value.startswith("LIST:"):
                    val = value[len("LIST:"):]
                    new_object.__dict__[key] = [ token.strip() for token in val.split(",") ]
                else:
                    new_object.__dict__[key] = value
    return new_object

def delete(id_value, id_column, filename, table_name):
    query = "DELETE FROM [{0}] WHERE [{1}] = ?".format(table_name, id_column)
    db_execute(filename, query, [id_value])

def insert_or_update_generic(object, filename):
    meta = object.get_meta()
    query = "SELECT [{0}] FROM [{1}] WHERE [{0}] = ?".format(meta.id_column, meta.table_name)
    if db_fetch_one(filename, query, [object.get_id()]):
        update_generic(object, filename, meta.table_name)
    else:
        insert_generic(object, filename, meta.table_name, False)
    
def insert_generic(object, filename, replace_into=False):
    meta = object.get_meta()
    keys = []
    values = []
    columns_str = None
    values_str = None
    for key, value in vars(object).items():
        if value is not None and not key in meta.ignore_list:
            keys.append(key)
            if isinstance(value, types.ListType):
                values.append("LIST:" + ",".join(value))
            else:
                values.append(value)
            if columns_str:
                columns_str = "{0},[{1}]".format(columns_str, key)
            else:
                columns_str = "[{0}]".format(key)
            if values_str:
                values_str = values_str + ",?"
            else:
                values_str = "?"
    query = "INSERT{0} INTO [{1}] ({2}) VALUES ({3})".format(" OR REPLACE" if replace_into else "", meta.table_name, columns_str, values_str)
    return db_execute(filename, query, values)
    
def update_generic(object, filename):
    meta = object.get_meta()
    id_value = object.get_id()
    keys = []
    values = []
    set_str = None
    for key, value in vars(object).items():
        if value and (not key in meta.ignore_list):
            keys.append(key)
            if isinstance(value, types.ListType):
                values.append("LIST:" + ",".join(value))
            else:
                values.append(value)
            if set_str:
                set_str = "{0},[{1}]=?".format(set_str, key)
            else:
                set_str = "[{0}]=?".format(key)
    query = "UPDATE [{0}] SET {1} WHERE [{2}]=?".format(meta.table_name, set_str, meta.id_column)
    values.append(id_value)
    db_execute(filename, query, values)

def db_fetch_one(filename, query, values=[]):
    conn = sqlite3.connect(filename)
    conn.row_factory = sqlite3.Row
    return conn.execute(query, values).fetchone()

def db_fetch_all(filename, query, values=[]):
    conn = sqlite3.connect(filename)
    conn.row_factory = sqlite3.Row
    return conn.execute(query, values).fetchall()
    
def db_execute(filename, query, values=[]):
    last_id = None
    conn = sqlite3.connect(filename, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()
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
