import sqlite3



def connect_db_except(expt):
    conn = sqlite3.connect("./data/user.db")
    cursor = conn.cursor()
    cursor.execute("create table if not exists Cookies(id integer primary key, user_id varchar)")
    cursor.execute(expt)
    pua = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()

    return pua