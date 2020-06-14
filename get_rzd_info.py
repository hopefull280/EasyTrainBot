import datetime
import random
import re
import requests
import time
import config


def in_dictionary(key, dict):
    if key in dict:
        return False
    return True


def set_params(user_data: dict):
    params = {
        'STRUCTURE_ID': 735,
        'layer_id': 5827,
        'dir': 0,
        'tfl': 3,
        'checkSeats': 1,
        'code0': user_data['FROM'],
        'code1': user_data['TO'],
        'dt0': user_data['DATE'],
        'md': 0
    }
    return params


def get_info(params):
    path = 'https://pass.rzd.ru/timetable/public/'
    sess = requests.session()
    user_agent = random.choice(config.user_agent_list)
    headers = {'User-Agent': user_agent}
    sess.headers = headers
    resp = sess.get(path, params=params)
    if 'RID' in resp.json():
        rid = resp.json()['RID']
        params['rid'] = rid
    time.sleep(2)
    train_info = sess.get(path, params=params)
    train = train_info.json()
    tickets_info = []
    one_train = {}
    cars = []
    one_car = {}
    route_info = {}
    for d in train['tp']:
        route_info['from'] = d['from']
        route_info['where'] = d['where']
        route_info['date'] = d['date']
    for d in train['tp'][0]['list']:
        one_train['number'] = d['number']
        if d['brand']:
            one_train['brand'] = d['brand']
        one_train['from_station'] = d['station0']
        one_train['where_station'] = d['station1']
        one_train['from_time'] = d['time0']
        one_train['where_time'] = d['time1']
        one_train['timeInWay'] = d['timeInWay']
        for k in d['cars']:
            if in_dictionary('disabledPerson', k):
                one_car['type'] = k['type']
                one_car['freeSeats'] = k['freeSeats']
                one_car['tariff'] = k['tariff']
                cars.append(one_car)
                one_car = {}
        one_train['cars'] = cars
        cars = []
        tickets_info.append(one_train)
        one_train = {}
    return tickets_info


def get_sale(tickets_info: list):
    k, i = 0, 0
    train = {}
    ticket = {}
    cheapest = 99999
    while k < len(tickets_info):
        while i < len(tickets_info[k]['cars']):
            if int(tickets_info[k]['cars'][i]['tariff']) < cheapest:
                cheapest = tickets_info[k]['cars'][i]['tariff']
                train = tickets_info[k]
                ticket = tickets_info[k]['cars'][i]
            i += 1
        k += 1
    user_text = ''
    if 'brand' in train:
        user_text = "*Бренд:* {brand} \n".format(**train)
    user_text += """
    *Номер поезда:* {number}
    *Станция отправления:* {from_station}
    *Станция прибытия:* {where_station}
    *Время отправления:* {from_time}
    *Время прибытия:* {where_time}
    *Время в пути:* {timeInWay} \n""".format(**train)
    user_text += """
    *Тип:* {type}
    *Свободные места:* {freeSeats}
    *Цена:* {tariff} \n""".format(**ticket)
    return user_text


def get_date(date_text):
    replaced = re.sub('[-. ]', '.', date_text)
    result = re.findall(r'\d{2}.\d{2}.\d{4}', replaced)
    print(result[0])


def check_date(date_text):
    replaced = re.sub('[-. ]', '.', date_text)
    try:
        result = re.findall(r'\d{2}.\d{2}.\d{4}', replaced)
        vld_date = datetime.datetime.strptime(result[0], '%d.%m.%Y')
        delta = vld_date.date() - datetime.date.today()
        if delta.days < 0:
            return True
        elif delta.days > 40:
            return True
        else:
            return result[0]
    except ValueError:
        return True


def valid_date(date_text):
    replaced = re.sub('[-. ]', '.', date_text)
    return replaced


def get_station_code(input_name):
    params = {
        'Query': input_name,
        'Language': 'ru',

    }
    path = 'https://ticket.rzd.ru/isdk/suggests'
    resp = requests.get(path, params=params)
    state = resp.json()
    if state['total_count'] == 0:
        return None
    else:
        return state['transport_node_suggests'][0]['ExpressCode']

