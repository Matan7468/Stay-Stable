import smtplib
import mysql.connector
from flask import json
from datetime import datetime ,timedelta
import logging
import os
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import math
import numpy as np


if not os.path.exists('logs'):#creation of logs folder
    os.makedirs('logs')

request_count = 0
format = logging.Formatter("%(asctime)s.%(msecs)03d %(levelname)s: %(message)s | request #%(request_count)s","%d-%m-%Y %H:%M:%S")
logger_name = "logger"
logger = logging.getLogger(logger_name)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("logs/{}.log".format(logger_name), mode='w')#creation of log file
file_handler.setFormatter(format)
logger.addHandler(file_handler)


config = {
    'user': 'uxbfzkjfzlxiefpm',
    'password': 'o2uM7IOSVhlI0yu2yUF2', 
    'host': 'bso1emke9kuwl56sroz2-mysql.services.clever-cloud.com',
    'database': 'bso1emke9kuwl56sroz2',
    'raise_on_warnings': True
}

def get_db_connection():
    return mysql.connector.connect(**config)


def send_email(table, first_name, last_name):
    # Set up the SMTP server
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_username = 'staystayble1@gmail.com'
    smtp_password = r'fztwumxbosycttno'
    smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
    smtp_connection.starttls()
    smtp_connection.login(smtp_username, smtp_password)

    # Set up the email content
    sender = 'staystayble1@gmail.com'
    recipient = table
    subject = 'ATTENTION! A fall has been detected'
    body = f'{first_name} {last_name} fell! please check that s/he is ok?'
    for i in recipient:
        if i is None or i == '':
            continue
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = i
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Send the email
        smtp_connection.sendmail(sender, i, msg.as_string())


    # Close the SMTP connection
    smtp_connection.quit()
def jsonize(cursor, result):
    if type(result) is not list:
        row_headers = [x[0] for x in cursor.description] #this will extract row headers
        return dict(zip(row_headers,result))
    else:#result is a list
        row_headers=[x[0] for x in cursor.description]
        json_data=[]
        for result in result:
            json_data.append(dict(zip(row_headers,result)))
        return json_data
    

def route_test(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    response = json.loads(request.data)
    print(response)
    return response

def Get_Vibrations(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'POST'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    id = dic['id']
    time_to_get = dic['time_to_get']

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    mac_query = f"SELECT crypted_mac FROM users WHERE id={id}"
    cursor.execute(mac_query)
    if cursor.rowcount != 0:
        crypted_mac = cursor.fetchone()[0]
        
        get_information_of_user = f""" SELECT date_time,encrypted_value,length  FROM vibrations WHERE crypted_mac='{crypted_mac}' AND date_time>='{time_to_get}' ORDER BY date_time ASC;"""
        cursor.execute(get_information_of_user)
        result_users = cursor.fetchall()
        formatted_results = []
        for result in result_users:
            parsed_date = datetime.strptime(str(result[0]), "%Y-%m-%d %H:%M:%S")
            formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            formatted_result = {
                "date_time": formatted_date,
                "value": decode_int_to_bool_list(result[1],result[2])
            }
            formatted_results.append(formatted_result)


        if cursor.rowcount != 0:
            logger.debug("vibrations were found successfuly", extra={"request_count": request_count})
            ans = 1
        else:
            logger.error("vibrations were not found", extra={"request_count": request_count})
            ans = 0
            result = "None"
        
    else:
        logger.error("Server encountered an error ! couldn't find user", extra={"request_count": request_count})
        ans = 0 # if the user is not in the database 
        result = "None"
    cursor.close()
    conn.close()
    
    return app.response_class(response=json.dumps({"answer": ans, "result": formatted_results}), mimetype='application/json')

    

def New_User(app, request):##- with mac
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

    dic = json.loads(request.data)
    mac = dic["mac"]
    first_name = dic["first_name"]
    last_name = dic["last_name"]
    age = dic["age"]
    medicine_name = dic["medicine_name"]
    email = dic["email"].lower()
    contacts = dic["contacts"]
    contact1, contact2, contact3 = "" , "" , ""
    length = len(contacts)
    if length >= 1:
        contact1 = contacts[0]
        if length >= 2:
            contact2 = contacts[1]
            if length >= 3:
                contact3 = contacts[2]
    if not re.fullmatch(regex, email):
        logger.error("Server encountered an error ! Invalid Email", extra={"request_count": request_count})
        result = "Server encountered an error ! Invalid Email"
        Status = 406
        ans = 0
        return app.response_class(response=json.dumps({"answer": ans, "result": result}), mimetype='application/json', status = Status)
    
    for c in contacts:
        if not re.fullmatch(regex, c):
            logger.error("Server encountered an error ! Invalid Email", extra={"request_count": request_count})
            result = "Server encountered an error ! Invalid Email"
            Status = 406
            ans = 0
            return app.response_class(response=json.dumps({"answer": ans, "result": result}), mimetype='application/json', status = Status)
        

    password = dic["password"]

    crypted_password = hashlib.sha256(password.encode()).hexdigest()
    crypted_mac = hashlib.sha256(mac.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    query_check = f"SELECT * FROM users WHERE email = '{email}'"
    cursor.execute(query_check)
    if cursor.rowcount != 0:
        logger.error("Server encountered an error ! user already exists for this email", extra={"request_count": request_count})
        result = "Server encountered an error ! user already exists for this email"
        Status = 400
        ans = 0
    else:
        record = (first_name, last_name, age, medicine_name, email, contact1, contact2, contact3, crypted_password, crypted_mac)

        # Check if any rows were returned
        sql = f"""INSERT INTO users (first_name, last_name, age, medicine_name, email, contact1, contact2, contact3, password, crypted_mac) VALUES (%s, %s, %s, %s, %s, %s, %s ,%s, %s, %s)"""
        cursor.execute(sql, record)
        
        if cursor.rowcount != 0:
            sql = f"SELECT id FROM users WHERE email = '{email}'"
            cursor.execute(sql)
            id = cursor.fetchone()[0]
            logger.debug("User added successfuly", extra={"request_count": request_count})
            conn.commit()
            ans = 1
            Status = 200
            result = id
        else:
            ans = 0
            logger.error("Server encountered an error !", extra={"request_count": request_count})
            result = "Server encountered an error !"
            Status = 401

    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans, "result": result}), mimetype='application/json', status = Status)




def New_Contact(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    email = dic["email"]
    id = dic["id"]
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
        
    record = (email, id)

    sql = f"""INSERT INTO contacts (email, id) VALUES (%s, %s)"""
    cursor.execute(sql, record)
    
    check = cursor.rowcount 
    if check != 0:
        logger.debug("Contact added successfuly", extra={"request_count": request_count})
        conn.commit()
        ans = 1
    else:
        ans = 0
        logger.error("Server encountered an error !", extra={"request_count": request_count})
        return app.response_class(response=json.dumps({"answer": ans, "result": "Server encountered an error !"}),status = 401, mimetype='application/json')


    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')


def is_almost_straight_triangle(point1, point2, point3, threshold_degrees):
    def calculate_angle(p1, p2, p3):
        def dot_product(v1, v2):
            return sum((a * b) for a, b in zip(v1, v2))

        def magnitude(v):
            return math.sqrt(sum((a * a) for a in v))

        v1 = [p1[i] - p2[i] for i in range(len(p1))]
        v2 = [p3[i] - p2[i] for i in range(len(p3))]

        dot = dot_product(v1, v2)
        mag_v1 = magnitude(v1)
        mag_v2 = magnitude(v2)

        if mag_v1 == 0 or mag_v2 == 0:
            return None

        cos_theta = dot / (mag_v1 * mag_v2)
        angle_rad = math.acos(cos_theta)
        angle_deg = math.degrees(angle_rad)
        return angle_deg

    angle1 = calculate_angle(point1, point2, point3)
    angle2 = calculate_angle(point2, point3, point1)
    angle3 = calculate_angle(point3, point1, point2)

    # Check if any of the angles are close to 180 degrees
    if angle1 is not None and abs(angle1 - 180) < threshold_degrees:
        return True
    if angle2 is not None and abs(angle2 - 180) < threshold_degrees:
        return True
    if angle3 is not None and abs(angle3 - 180) < threshold_degrees:
        return True

    return False


def count_pairs_with_speed_c(coordinates):
    # Count the number of pairs with speeds exceeding 4 Hz and not forming an almost straight triangle
    ret_list = [False] * len(coordinates)
    temp_list = list()
    temp_list_index = list()
    delta_time = 2.0 / len(coordinates)
    # Print the pairs of coordinates with speeds exceeding 4 Hz
    for i in range(len(coordinates) - 1):
        point1 = np.array(coordinates[i])
        point2 = np.array(coordinates[i + 1])
        speed = calculate_speed(point1, point2) / delta_time  # Calculate the speed between the two points
        if speed >= 4.0 and speed <= 6.0:
            temp_list.append([point1, point2])
            temp_list_index.append(i)

    for index, i in zip(range(len(temp_list)-1), range(len(temp_list_index)-1)):
        ret_list[temp_list_index[i]] = not (np.array_equal(temp_list[index][1], temp_list[index+1][0]) and is_almost_straight_triangle(temp_list[index][0], temp_list[index][1], temp_list[index+1][1], 15))
    
    if len(temp_list_index)-1 > 0:
        ret_list[temp_list_index[-1]] = True
    return ret_list


def calculate_speed(point1, point2):
    # Calculate the speed between two 3D coordinates (points)
    # Replace this with your own calculation based on the coordinate values
    # For example, you can calculate the Euclidean distance or any other suitable method
    return np.linalg.norm(point2 - point1)  # Example: Using Euclidean distance as the speed

def count_coordinates_with_speed(vibrations):
    my_list = count_pairs_with_speed_c(vibrations)
    encode = encode_bool_list_to_int(my_list)
    return encode, len(my_list)        


def encode_bool_list_to_int(bool_list):
    encoded_int = 0
    for i, value in enumerate(bool_list):
        if value:
            encoded_int |= (1 << i)
    return encoded_int

def decode_int_to_bool_list(encoded_int, length):
    bool_list = []
    for i in range(length):
        bool_list.append((encoded_int & (1 << i)) != 0)
    return bool_list


def Input_Information(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    vibrations = dic["vibrations"]
 
    mac = dic["mac"]
    
    sum_vibrations, length = count_coordinates_with_speed(vibrations)
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    crypted_mac = hashlib.sha256(mac.encode()).hexdigest()
    
    record = (crypted_mac, dt_string, sum_vibrations, length)
    sql = f"""INSERT INTO vibrations (crypted_mac, date_time, encrypted_value, length) VALUES (%s, %s, %s, %s)"""
    cursor.execute(sql, record)
    check = cursor.rowcount
    if check != 0:
        logger.debug("vibrations were added successfuly", extra={"request_count": request_count})
        conn.commit()
        ans = 1
    else:
        ans = 0
        logger.error("Server encountered an error !", extra={"request_count": request_count})
        cursor.close()
        conn.close()
        return app.response_class(response=json.dumps({"answer": ans, "result": "Server encountered an error !"}),status = 401, mimetype='application/json')

    
    cursor.close()
    conn.close()

    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')


    
def Input_Alert(app, request):#1 for alert, 0 for no alert ###### notify the app somehow?
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    mac = dic["mac"]
    crypted_mac = hashlib.sha256(mac.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    user_query = f"SELECT id, first_name, last_name, contact1, contact2, contact3 FROM users WHERE crypted_mac = '{crypted_mac}';"
    cursor.execute(user_query)
    user_row = cursor.fetchone()

    if cursor.rowcount !=0:
        user_id = user_row[0]
        user_first_name = user_row[1]
        user_last_name = user_row[2]
        emails = user_row[3:5]
        send_email(emails, user_first_name, user_last_name)
        logger.debug("Emails were sent successfuly", extra={"request_count": request_count})
        ans = 1
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        record = (user_id, dt_string)
        fall_query = f"INSERT INTO falls (user_id, date_time) VALUES (%s, %s);"
        cursor.execute(fall_query, record)
        conn.commit()
    else:
        logger.error("Server encountered an error ! couldn't find the user", extra={"request_count": request_count})
        ans = 0
        return app.response_class(response=json.dumps({"answer": ans, "result": "Server encountered an error ! couldn't find the user"}),status = 401, mimetype='application/json')
        

    cursor.close()
    conn.close()

    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')

def Check_Connection(app, request):#returns 1 if status changed and 0 if not
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})
    print(request.data)
    dic = json.loads(request.data)
    mac = dic["mac"]
    new_status = dic["status"]
    crypted_mac = hashlib.sha256(mac.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    cursor.execute(f"UPDATE users SET status = {new_status} WHERE crypted_mac = '{crypted_mac}'")
    if cursor.rowcount != 0:
        logger.debug("Status was updated successfuly", extra={"request_count": request_count})
        conn.commit()
        ans = 1
    else:
        logger.debug("Status was remained the same", extra={"request_count": request_count})
        ans = 0
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')

def Get_Status(app, request):# if status is -1- code error 0- no connection, 1- connection, 2- not connection and notified
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    id = dic["id"]

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute(f"SELECT status FROM users WHERE id = {id}")
    if cursor.rowcount != 0:
        logger.debug("Status was retrieved successfuly", extra={"request_count": request_count})
        current_status = cursor.fetchone()[0]

        if current_status == 0:
            cursor.execute(f"UPDATE users SET status = {2} WHERE  id = {id}")
            if cursor.rowcount != 0:
                logger.debug("Status was updated successfuly", extra={"request_count": request_count})
                conn.commit()
            else:
                logger.error("Server encountered an error ! couldn't update status", extra={"request_count": request_count})
                current_status = -1
        elif current_status == 2:
            logger.debug("Status has remained the same", extra={"request_count": request_count})
    else:
        logger.error("Server encountered an error ! couldn't find status for this id", extra={"request_count": request_count})
        current_status = -1
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"status": current_status}), mimetype='application/json')

def Update_Information(app, request):#1 if there was a change 0 if there wasn't
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    id = dic["id"]
    first_name = dic["first_name"]
    last_name = dic["last_name"]
    email = dic["email"]
    password = dic["password"]
    contacts = dic["contacts"]
    if len(contacts) < 3:
        contacts.append("")
        if len(contacts) < 2:
            contacts.append("")

    print(contacts)
    crypted_password = hashlib.sha256(password.encode()).hexdigest()
    add_passsword = ""
    if not password == "":
        add_passsword = f", password = '{crypted_password}'"
    

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    query = f"""UPDATE users SET  first_name = '{first_name}', last_name = '{last_name}', 
                   email = '{email}', contact1 = '{contacts[0]}', contact2 = '{contacts[1]}', contact3 = '{contacts[2]}' """ + add_passsword + f"""
                   WHERE id = {id};"""
    cursor.execute(query)
    if cursor.rowcount != 0:
        logger.debug("Information was updated successfuly", extra={"request_count": request_count})
        conn.commit()
        ans = 1
    else:
        logger.debug("No new information was added.", extra={"request_count": request_count})
        ans = 0

    cursor.close()
    conn.close()

    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')


def Last_dose(app, request):#returns the last dose: table if found -1 if not found
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    id = dic["id"]
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute(f"SELECT dosage, date_time FROM dosages WHERE user_id = {id} order by date_time desc")
    if cursor.rowcount != 0:
        ans = 1
        logger.debug("Last dose was retrieved successfuly", extra={"request_count": request_count})
        tuple_last_dose = cursor.fetchone()
        list_last_dose = list(tuple_last_dose)
        list_last_dose[1] = list_last_dose[1].strftime("%d-%m-%Y %H:%M") # change it back to application format
        date, time = list_last_dose[1].split(" ")
        ret = {"dosage": list_last_dose[0], "date": date, "time": time}

    else:
        last_dose = "Server encountered an error ! couldn't find last dose for this id"
        logger.error(last_dose , extra={"request_count": request_count})
        ans = 0
        ret = {"dosage": "not found", "date": "not found", "time": "not found"}
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans, "result": ret}), mimetype='application/json')


def get_user(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'POST'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    user_id = dic["id"]
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
    user = cursor.fetchone()
    user = jsonize(cursor, user)
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": 1, "user": user}), mimetype='application/json')


def get_doses_history(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'POST'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    user_id = dic["id"]
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute(f"SELECT * FROM dosages WHERE user_id = {user_id} order by date_time desc")
    doses = cursor.fetchall()
    doses = jsonize(cursor, doses)
    ret = []
    for dose in doses:
        dose["date_time"] = dose["date_time"].strftime("%d-%m-%Y %H:%M") # change it back to application format
        date, time = dose["date_time"].split(" ")
        ret.append({"dosage":dose["dosage"], "date":date, "time":time})
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": 1, "doses": ret}), mimetype='application/json')

def Input_Dose(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    user_id = dic["id"]
    dosage = dic["dosage"]
    date = dic["date"] #format of dd/mm/yyyy
    time = dic["time"] #format of hh:mm
    formated_date = datetime.strptime(date, "%d-%m-%Y").strftime('%Y-%m-%d')
    formated_date = formated_date + " " + time

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    record = (user_id, dosage, formated_date)
    sql = f"insert into dosages (user_id, dosage, date_time) values (%s, %s, %s)"
    cursor.execute(sql, record)
    check = cursor.rowcount
    if check != 0:
        logger.debug("dosage was added successfuly", extra={"request_count": request_count})
        conn.commit()
        ans = 1
    else:
        ans = 0
        logger.error("Server encountered an error !", extra={"request_count": request_count})

    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')


def get_day_info(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})
    dic = json.loads(request.data)
    user_id = dic["id"]
    date = dic["date"]
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    dosage_query = f"SELECT dosage, TIME_FORMAT(date_time, '%H:%i') FROM dosages WHERE DATE(date_time)='{date}' AND user_id={user_id}"
    cursor.execute(dosage_query)
    dosages = cursor.fetchall()
    dosages = [(d[0], str(d[1])) if isinstance(d[1], timedelta) else d for d in dosages]

    fall_query = f"SELECT TIME_FORMAT(date_time, '%H:%i') FROM falls WHERE DATE(date_time)='{date}' AND user_id={user_id}"
    cursor.execute(fall_query)
    falls = cursor.fetchall()
    falls = [(str(f[0])) if isinstance(f[0], timedelta) else f[0] for f in falls]
    cursor.close()
    conn.close()
    merged_times = [time for _, time in dosages] + falls
    datetime_times = [datetime.strptime(time, "%H:%M") for time in merged_times]
    
    merged_list = dosages + list(zip([None]*len(falls), falls))
    merged_list.sort(key=lambda x: datetime.strptime(x[1], "%H:%M"))

    return app.response_class(response=json.dumps({"list": merged_list}), mimetype='application/json')


def Login(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    email = dic["email"].lower()
    password = dic["password"]
    crypted_password = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute(f"SELECT * FROM users WHERE email = '{email}' AND password = '{crypted_password}'")
    if cursor.rowcount != 0:
        logger.debug("User was found successfuly", extra={"request_count": request_count})
        user = cursor.fetchone()
        user = jsonize(cursor, user)
        if user["password"] == crypted_password:
            logger.debug("Password was correct", extra={"request_count": request_count})
            ans = 1
        else:
            logger.debug("Password was incorrect", extra={"request_count": request_count})
            ans = 0
            user = "None"
    else:
        logger.error("Server encountered an error ! couldn't find user", extra={"request_count": request_count})
        ans = -1
        user = "None"
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans, "user": user}), mimetype='application/json')


def get_all_history(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    id = dic["id"]

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute(f"""SELECT DATE(date_time) AS day, COUNT(*) AS dose_count, GROUP_CONCAT(dosage SEPARATOR ' ') AS dosage
                        FROM dosages
                        WHERE user_id = {id}
                        AND date_time >= DATE_SUB(NOW(), INTERVAL 1 WEEK)
                        GROUP BY DATE(date_time);""")

    if cursor.rowcount != 0:
        logger.debug("dosages found successfuly!", extra={"request_count": request_count})
        doses = cursor.fetchall()
        ret=[]
        for row in doses:
            day = row[0].strftime("%d-%m-%Y %H:%M") # change it back to application format
            date, time = day.split(" ")

            dose_count = row[1]
            dosage = row[2].split(" ")
            for i in range(len(dosage)):
                dosage[i] = int(dosage[i])
            ret.append({"dosages":dosage, "dosage_count":dose_count, "date":date})
        ans = 1
    else:
        logger.debug("dosages not found!", extra={"request_count": request_count})
        ans = 0
        ret = None
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans, "dosages": ret}), mimetype='application/json')

def reset_password(app, request):
    global request_count
    request_count += 1
    logger.info("Incoming request | #{} | resource: {} | HTTP Verb {}".format(request_count, '/logs/level', 'GET'), extra={"request_count": request_count})

    dic = json.loads(request.data)
    email = dic["email"].lower()
    password = dic["password"]
    crypted_password = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute(f"UPDATE users SET password = '{crypted_password}' WHERE email = '{email}'")
    if cursor.rowcount != 0:
        logger.debug("Password was updated successfuly", extra={"request_count": request_count})
        conn.commit()
        ans = 1
    else:
        logger.error("Server encountered an error ! couldn't update password", extra={"request_count": request_count})
        ans = 0
    cursor.close()
    conn.close()
    return app.response_class(response=json.dumps({"answer": ans}), mimetype='application/json')
