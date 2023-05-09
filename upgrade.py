# -*- coding: UTF-8 -*-

import json
import os
import re
import sys
import time

from classes import Client

from multiprocessing import Manager, Process


def raise_exception(exception): sys.exit("[!] {}".format(exception))


if __name__ == '__main__':

    st = time.time()

    with open(os.path.join(os.path.dirname(__file__), 'upgrade.txt'), 'r', \
        encoding='utf-8') as file:     

        keepass_db = keepass_pwd = ftp_server = None
        upgrade_steps_info = []

        line = file.readline()
        while line != '':

            if 'Root Directory:' in line:
                next_line = file.readline()
                root_dir = next_line.split('>')[1].strip() if '>' in next_line and \
                    len(set(next_line)) > 2 else raise_exception('Root directory not specified')

            elif 'Client Name:' in line:
                next_line = file.readline()
                client_name = next_line.split('>')[1].strip() if '>' in next_line and \
                    len(set(next_line)) > 2 else raise_exception('Client name not specified')
            
            elif 'Keepass Database:' in line:
                next_line = file.readline()
                keepass_db = next_line.split('>')[1].strip() if '>' in next_line and \
                    len(set(next_line)) > 2 and '.kdbx' in next_line else \
                        raise_exception('Keepass database not specified')
                # keepass_pwd = input("[>] Keepass password: ")
                keepass_pwd = 'HOX265huq#'
            
            elif 'FTP Server' in line:
                next_line = file.readline()
                ftp_server = next_line.split('>')[1].strip() if '>' in next_line and \
                    len(set(next_line)) > 2 else raise_exception('Root directory not specified')

            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                upgrade_steps_info.append(info_requested)
            
            line = file.readline()

    client = Client(root_dir, client_name, keepass_db=keepass_db, keepass_pwd=keepass_pwd, \
        ftp_server=ftp_server)
    manager = Manager()
    report = manager.list()

    process_list = []
    for devive in client.device_list:
        # Append in a list the process of acquiring information for the device
        process = Process(target=devive.run_upgrade, args=(upgrade_steps_info, report))
        process_list.append(process)

    # Initiate the process of acquiring configurations for each device
    for process in process_list:
        process.start()
    # Wait for each process to finish
    for process in process_list:
        process.join()

    # Generage reports for this script
    client.report = report
    client.generate_upgrade_report()

    # Save all script output in a json file
    with open(f"{client.dir}/outputfiles/script_output.json", "w") as outfile:
        outfile.write(json.dumps(list(report), indent=2))

    print('Execution time:', time.time() - st, 'seconds')

    '''

    5. validar hash
        5.1 se hash ok -> ok
        5.2 se não ok
            5.2.1 delete imagem -> error (fazer manualmente)
    6. correr aqueles comandos e guardar num ficheiro .txt (append) 
    7. show tech para flash
    8. copiar show tech para ftp
    9. gerar report com tudo o que correu bem (a nivel de hash, copia, etc)
    10. gerar report dos comandos (ok e unsupported)

    terça-feira
        18 switches

    servidor (172.26.0.1) admin superadmin
    2960 e 35XX é preciso de copiar as imagens para todas as flash
    9k e 

'''
