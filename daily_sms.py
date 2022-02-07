from pyvcloud.vcd.client import BasicLoginCredentials
from pyvcloud.vcd.client import Client
from pyvcloud.vcd.system import System
from pyvcloud.vcd.vdc import PVDC
from pyvcloud.vcd.utils import pvdc_to_dict, vdc_to_dict
import requests
import datetime
import sys
import getpass




#глобальные переменнные
incorrect_login = 0
stor_tiers = {}
dict_2_0 ={}
dict_3_0 ={}
dict_62_0 ={}
vcd_admin_user = ""



HOST = "any.host.com:443"
HOST62 = "any.host.com:443"


#функция проверки ввода и авторизации
def auth(incorrect_login=None,incorrect_login62=None):
    global vcd_admin_password 
    global vcd_admin_password62
    if len(sys.argv) < 3 or incorrect_login == 1 or incorrect_login62 == 1:
        print("\nRecommended:\nUsage cli: login password_public password_pci \n")
        if incorrect_login == 0:
            print("Параметры запуска не заданы, требуется ручно ввод УЗ.")
        else:
            pass
            # print("Параметры запуска не заданы, требуется ручно ввод УЗ.")
        vcd_admin_user = input ("Введите логин: ")
        vcd_admin_password = getpass.getpass("Введите пароль: ")
        # print("Следующее поле не обязательно для заполнения, можно просто нажать Enter")
        vcd_admin_password62 = getpass.getpass("Введите пароль PCI (опционально): ")
        if len(vcd_admin_password62) > 2:
            print("Заглянем ещё и в 62 облако значит")
    else:
        if len(sys.argv) == 3:
            vcd_admin_user = sys.argv[1]
            vcd_admin_password = sys.argv[2]
            vcd_admin_password62 = ""
        if len(sys.argv) == 4:
            vcd_admin_user = sys.argv[1]
            vcd_admin_password = sys.argv[2]
            print("Заглянем ещё и в 62 облако значит")
            vcd_admin_user62 = sys.argv[1]
            vcd_admin_password62 = sys.argv[3]
        
    vcd_admin_user62 = vcd_admin_user

    requests.packages.urllib3.disable_warnings()

    #пробую авторизоваться + создание клиента public
    print("Logging in: host={0}, user={1}".format(HOST, vcd_admin_user))
    global client
    client = Client(HOST, verify_ssl_certs=False,
                    log_file=None,
                    log_requests=False,
                    log_headers=False,
                    log_bodies=False)

    try:
        
        client.set_credentials(BasicLoginCredentials(vcd_admin_user,"system", vcd_admin_password))
    except:
        print(f"Подключение к {HOST} не установлено. Возможные причины:\n1)Отсутствует сетевое подключение\n2)Не корректно введены логин и/или пароль")
        print("Повторная попытка ввода УЗ")
        auth(incorrect_login=1)

    #если введен пароль для 62, авторизируемся + создаём клиента 62
    if len(vcd_admin_password62) > 2:
        print("Logging in PCI: host={0}, user={1}".format(HOST62, vcd_admin_user62))
        global client62
        client62 = Client(HOST62, verify_ssl_certs=False,
                        log_file=None,
                        log_requests=False,
                        log_headers=False,
                        log_bodies=False)
        try:
            
            client62.set_credentials(BasicLoginCredentials(vcd_admin_user62,"system", vcd_admin_password62))
        except:
            print(f"Подключение к {HOST62} не установлено. Возможные причины:\n1)Отсутствует сетевое подключение\n2)Не корректно введены логин и/или пароль")
            print("Повторная попытка ввода УЗ")
            auth(incorrect_login62=1)
    else:
        pass

#функция сбора информации, фактически основная
def get_pvdc_info(client):
    #cоздаю сущность System, необходима для дальнейше работы с  Provider VDC
    system = System(client,admin_resource=client.get_admin())
    #получаю информацию по всем имеющимся стореджам в облаке

    provider_vdcs_storage = system.list_provider_vdc_storage_profiles()
    for storage in sorted(provider_vdcs_storage):
        #получаю параметры каждого, конкретного storage
        storage_name = storage.get("name")
        storage_used = storage.get("storageUsedMB")
        storage_toral = storage.get("storageTotalMB")
        #до проверка, на случай если сторедж пуской( как в DEV)
        if int(storage_toral) > 0:
            stor_tiers[storage_name] = str(round(int(storage_toral)/1048576)),str(round((int(storage_used)/int(storage_toral))*100))
        else:
            #если пустой в качестве значений всего / % исользованя - "None"
            stor_tiers[storage_name] = "None","None"

    #получаю  перечесь всем PVDC
    provider_vdcs = system.list_provider_vdcs()
    #из полученнго списка, работаю с каждым PVDC по отдельности
    for pvdcs in provider_vdcs:
        # print(pvdcs.get("name"))
        #получаю ссылку на  PVDC
        pvdcs_href = pvdcs.get("href")
        #на основании ссылки, создаю объект класса PVDC
        pvdc_class = PVDC(client,href=pvdcs_href)
        #получаю в XML предсталвении все ресурсы этого PVDC
        pvdc = pvdc_class.get_resource()
        #из пакета utils.py беру функцию pvdc_to_dict( название говорит само за себя)
        pvdc_class_dict = pvdc_to_dict(pvdc)
        #далее реботаю как со словарём, в котором вся информацию по PVDC 
        #получаю информацию по RAM в данном PVDC
        pvdc_mem = pvdc_class_dict["mem_capacity"]
        pvdc_mem_total = round(int(pvdc_mem["total"])/1024,2)
        pvdc_mem_allocation = round(int(pvdc_mem["allocation"])/1024,2)
        pvdc_mem_used_procents =  round( (pvdc_mem_allocation / pvdc_mem_total) *100,2)
        #наполняю словарь dict_2_0 параметрами относязимися к кластеру 2.0
        print("pvdcs.get(name): ",pvdcs.get("name"))
        if "2.0" in pvdcs.get("name"):
            dict_2_0["Cloud-Tier-1"]=stor_tiers["Cloud-Tier-1"]
            dict_2_0["Cloud-Tier-2"]=stor_tiers["Cloud-Tier-2"]
            dict_2_0["Cloud-Tier-3"]=stor_tiers["Cloud-Tier-3"]
            dict_2_0["Cloud-Tier-4"]=stor_tiers["Cloud-Tier-4"]
            dict_2_0["pvdc_mem_total"]=round(pvdc_mem_total / 1024)
            dict_2_0["pvdc_mem_used_procents"]=pvdc_mem_used_procents
            print("\n","Получение данных по 2.6 кластеру :\n",dict_2_0,"\n\n")
        #наполняю словарь dict_3_0 параметрами относязимися к кластеру 3.0
        if "3.0" in pvdcs.get("name"):
            dict_3_0["c01-cl02-Tier-1"]=stor_tiers["c01-cl02-Tier-1"]
            dict_3_0["c01-cl02-Tier-2"]=stor_tiers["c01-cl02-Tier-2"]
            dict_3_0["c01-cl02-Tier-3"]=stor_tiers["c01-cl02-Tier-3"]
            dict_3_0["c01-cl02-Tier-4"]=stor_tiers["c01-cl02-Tier-4"]
            dict_3_0["pvdc_mem_total"]=round(pvdc_mem_total / 1024)
            dict_3_0["pvdc_mem_used_procents"]=pvdc_mem_used_procents
            print("\n","Получение данных по 3.0 кластеру :\n",dict_3_0,"\n\n")

        
        if "62" in pvdcs.get("name"):
            dict_62_0["Tier-1"]=stor_tiers["Tier-1"]
            dict_62_0["Tier-2"]=stor_tiers["Tier-2"]
            dict_62_0["Tier-3"]=stor_tiers["Tier-3"]
            dict_62_0["Tier-4"]=stor_tiers["Tier-4"]
            dict_62_0["pvdc_mem_total"]=round(pvdc_mem_total / 1024)
            dict_62_0["pvdc_mem_used_procents"]=pvdc_mem_used_procents
            print("\n","Получение данных по PCI кластеру :\n",dict_62_0,"\n\n")
        else:
            #если инфы по PVDC нет - забиваю все данные нулями, актуально при использовании без доступа в PCI
            dict_62_0["Tier-1"]="0","0"
            dict_62_0["Tier-2"]="0","0"
            dict_62_0["Tier-3"]="0","0"
            dict_62_0["Tier-4"]="0","0"
            dict_62_0["pvdc_mem_total"]="0"
            dict_62_0["pvdc_mem_used_procents"]="0"
    client.logout()

#вызываю авторизацию
auth()
#получаю инфу из из 1 кластера
get_pvdc_info(client)

#получаю инфу из 2 пластера, при условвии что пароль задан
if len(sys.argv) == 4  or len(vcd_admin_password62) > 1:
    get_pvdc_info(client62)

#получаю текущую дату
cdt=datetime.datetime.now()
#получаю "вчера"
yesterday= cdt -  datetime.timedelta(days=1)

#полученную дату перводу в формат   ['23', '06','21']
list_cdt=datetime.datetime.strftime(cdt,'%d %m %y').split()
list_yesterday = datetime.datetime.strftime(yesterday,'%d %m %y').split()


resault_str = f"""Ежедневный отчёт за 24 часа
Период: с {int(list_yesterday[0])}.{list_yesterday[1]}.20{list_yesterday[2]} 20:30 по {int(list_cdt[0])}.{list_cdt[1]}.20{list_cdt[2]} 20:30
=== Утилизация RAM, TB ===
IaaS Prod 2.6: {dict_2_0.get("pvdc_mem_total")} ({dict_2_0.get("pvdc_mem_used_procents")}%)
IaaS Prod 3.0: {dict_3_0.get("pvdc_mem_total")} ({dict_3_0.get("pvdc_mem_used_procents")}%)
IaaS-62: {dict_62_0.get("pvdc_mem_total")} ({dict_62_0.get("pvdc_mem_used_procents")}%)

= Утилизация Storage, TB =
IaaS Prod 2.6
Tier-1: {dict_2_0.get("Cloud-Tier-1")[0]} ({dict_2_0.get("Cloud-Tier-1")[1]}%)
Tier-2: {dict_2_0.get("Cloud-Tier-2")[0]} ({dict_2_0.get("Cloud-Tier-2")[1]}%)
Tier-3: {dict_2_0.get("Cloud-Tier-3")[0]} ({dict_2_0.get("Cloud-Tier-3")[1]}%)
Tier-4: {dict_2_0.get("Cloud-Tier-4")[0]} ({dict_2_0.get("Cloud-Tier-4")[1]}%)

IaaS Prod 3.0
Tier-1: {dict_3_0.get("c01-cl02-Tier-1")[0]} ({dict_3_0.get("c01-cl02-Tier-1")[1]}%)
Tier-2: {dict_3_0.get("c01-cl02-Tier-2")[0]} ({dict_3_0.get("c01-cl02-Tier-2")[1]}%)
Tier-3: {dict_3_0.get("c01-cl02-Tier-3")[0]} ({dict_3_0.get("c01-cl02-Tier-3")[1]}%)
Tier-4: {dict_3_0.get("c01-cl02-Tier-4")[0]} ({dict_3_0.get("c01-cl02-Tier-4")[1]}%)

IaaS-62:
Tier-1: {dict_62_0.get("Tier-1")[0]} ({dict_62_0.get("Tier-1")[1]}%)
Tier-2: {dict_62_0.get("Tier-2")[0]} ({dict_62_0.get("Tier-2")[1]}%)
Tier-3: {dict_62_0.get("Tier-3")[0]} ({dict_62_0.get("Tier-3")[1]}%)
Tier-4: {dict_62_0.get("Tier-4")[0]} ({dict_62_0.get("Tier-4")[1]}%)

"""
print(resault_str) 

file_name =f"daily_sms_{list_cdt[0]}.{list_cdt[1]}.{list_cdt[2]}.txt"

# создание тхт с результатом + открытие блокнота с этим результатом
with open(f'{file_name}','w') as fp:
    fp.write(resault_str)
import subprocess as sp
programName = "notepad.exe"
sp.Popen([programName, file_name])

input("Для завершения работы программы, нажмите Enter.")