import MySQLdb
from MySQLdb.cursors import DictCursor

bak_db = 'xbmc_video75_bak'
new_db = 'xbmc_video_new75'


def db_fetch_one(db_name, query, values=None):
    cursor, conn = create_cursor(db_name)
    cursor.execute(query, values)
    one = cursor.fetchone()
    return one

def db_fetch_all(db_name, query, values=None):
    cursor, conn = create_cursor(db_name)
    cursor.execute(query, values)
    return cursor.fetchall()
    
def db_execute(db_name, query, values=None):
    last_id = None
    cursor, conn = create_cursor(db_name)
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

def create_cursor(db_name):
    conn = MySQLdb.connect(host='<TODO>', port=7010, user='<TODO>', passwd='<TODO>', db=db_name)
    return (conn.cursor(DictCursor), conn)



def import_all():
    query = 'update `files` set `playCount`=%s, `lastPlayed`=%s where `strFilename`=%s'
    rows = db_fetch_all(bak_db, 'select * from `files` where `lastPlayed` is not null or `playCount` is not null')
    for row in rows:
        db_execute(new_db, query, (row['playCount'], row['lastPlayed'], row['strFilename']))
        print row['strFilename'], ':', row['playCount'], 'total plays', row['lastPlayed'], 'last played'

    
if __name__ == "__main__":
    import_all()

    