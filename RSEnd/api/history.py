from flask import Blueprint, jsonify
import pymysql


history_bp = Blueprint('history', __name__)

# 2. 把所有和历史记录相关的接口都搬到这里
@history_bp.route('/', methods=['GET'])
def get_history():
    db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob', charset='utf8')
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM history_records ORDER BY created_at DESC")
    records = cursor.fetchall()
    cursor.close()
    db_conn.close()
    for record in records:
        if record.get('created_at'):
            record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(records)

@history_bp.route('/<int:record_id>', methods=['GET'])
def get_history_record(record_id):
    db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob', charset='utf8')
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM history_records WHERE id = %s", (record_id,))
    record = cursor.fetchone()  # fetchone() 用于获取单条记录

    cursor.close()
    db_conn.close()

    if record:
        return jsonify(record)
    else:
        return jsonify({"error": "找不到该条记录"}), 404

@history_bp.route('/<int:record_id>', methods=['DELETE'])
def delete_history(record_id):
    db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob', charset='utf8')
    cursor = db_conn.cursor()

    sql = "DELETE FROM history_records WHERE id = %s"
    cursor.execute(sql, (record_id,))

    db_conn.commit()
    cursor.close()
    db_conn.close()

    return jsonify({"message": "删除成功"})