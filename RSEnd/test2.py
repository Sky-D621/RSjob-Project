import pymysql

def adduser():
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', charset='utf8')
    cursor = conn.cursor()
    conn.commit()
    cursor.execute('use userinfo')
    username="555"
    password="555"
    sql = "insert into users (`username`, `password`)values('" + str(username) + "','" + str(password) + "');"
    print(sql)

    count = cursor.execute(sql)
    print(count)
    conn.commit()
    cursor.close()
    conn.close()
    return "success"

def serchall():
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', charset='utf8')
    cursor = conn.cursor()
    conn.commit()
    cursor.execute('use userinfo')
    sql = "select * from users;"
    count = cursor.execute(sql)
    data = cursor.fetchall()  # cursor.fetchall()
    tableData = []
    for i in range(count):
        datai = data[i]
        dataiJson = {"id": datai[0], "username": datai[1], "password": datai[2]}
        tableData.append(dataiJson)
    conn.commit()
    cursor.close()
    conn.close()
    return tableData


if __name__ == '__main__':
    tableData=serchall();
    print(tableData)