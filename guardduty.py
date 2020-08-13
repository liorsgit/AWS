#!/usr/bin/python

try:
  import sys
  import string
  import os
  import time
  from itertools import izip
  import re
  import boto3
  import json
  import csv
  import jsonplus as jplus
  from pprint import pprint
  from botocore.exceptions import ClientError

except ImportError:

    print "Cannot find module."
    raise


def loop():

      def list_accounts_from_parent(): # creates a new file with accouts info. origin: aws

        with open('accounts_from_parent.txt','w'): pass # makes the file empty for each run
        account = boto3.session.Session(profile_name='default', region_name='eu-west-1') # Session = Default (Organization access)
        client = account.client('organizations')
        with open('parentids.txt','r') as parents: # OU file to get accounts from
            for id in parents:
                id = id.strip("\n")

                # weak part- hardcoded. each row represents a request that is limited to 20 accounts. overall supports 100 accounts:

                response = client.list_accounts_for_parent(ParentId=id)
                response1 = client.list_accounts_for_parent(ParentId=id, NextToken=response['NextToken'])
                response2 = client.list_accounts_for_parent(ParentId=id, NextToken=response1['NextToken'])
                response3 = client.list_accounts_for_parent(ParentId=id, NextToken=response2['NextToken'])
                response4 = client.list_accounts_for_parent(ParentId=id, NextToken=response3['NextToken'])

                for res in [response, response1, response2, response3, response4]:
                    accounts = res['Accounts']
                    dict_len=len(accounts)
                    y = jplus.dumps(accounts, indent=4)
                    j = jplus.loads(y)

                    counter = 0
                    while counter < dict_len:
                        name =  j[counter]['Name']
                        email = j[counter]['Email']
                        id = j[counter]['Id']
                        with open('accounts_from_parent.txt', mode='a') as file: # Appends name,email,id to the empty file
                            writer = csv.writer(file, delimiter=',')
                            writer.writerow([id, name, email])
                        counter += 1


      def list_accounts_from_file(): # creates a new file with accouts info. origin: company local file

          with open('accounts_from_file.txt','w'): pass # makes the file empty for each run
          a=[]
          b=[]
          profiles = os.popen("cat ~/.aws/config | egrep '\[([^]]+)\]' | cut -d '[' -f2 | cut -d ']' -f1 | awk '{print $2}'") # gets the profiles ONLY
          for prof in profiles:
              prof_cli = prof.strip("\n")
              b.append(prof_cli)
          account_ids = os.popen("cat ~/.aws/config | grep -o -P '(?<=::).*(?=:)'") # gets the account_id ONLY
          for id in account_ids:
              id_cli = id.strip("\n")
              a.append(id_cli)

          with open('accounts_from_file.txt', 'wb') as f:
              writer = csv.writer(f)
              writer.writerows(izip(a, b))


      def merge_two_lists_a(): # for row in file - if in parentid - append

          with open('last_file_accounts_a.txt','w'): pass # makes the file empty for each run
          with open('accounts_from_file.txt', 'r') as file:
              for row in file:
                  id = [row.split(',')[0]]
                  id = id[0]
                  with open('accounts_from_parent.txt', 'r') as file2:
                      for row2 in file2:
                          id2 = [row2.split(',')[0]]
                          id2 = id2[0].strip('\r\n')
                          if id == id2:
                              with open('last_file_accounts_a.txt', 'a') as final:
                                  final.write(row)


      def merge_two_lists_b(): # for row in parentid - if in file - append

          with open('last_file_accounts_b.txt','w'): pass # makes the file empty for each run
          with open('accounts_from_parent.txt', 'r') as file:
              for row in file:
                  id = [row.split(',')[0]]
                  id = id[0]
                  with open('accounts_from_file.txt', 'r') as file2:
                      for row2 in file2:
                          id2 = [row2.split(',')[0]]
                          id2 = id2[0].strip('\r\n')
                          if id == id2:
                              with open('last_file_accounts_b.txt', 'a') as final:
                                  final.write(row)


      def create_member(): #enables guardduty

        list_of_dicts = []
        with open('last_file_accounts_b.txt', 'r') as file:
              for row in file:
                  id = [row.split(',')[0]]
                  id = id[0]
                  email = [row.split(',')[2]]
                  email = email[0].strip('\r\n')
                  list_of_dicts.append({'Email':email,'AccountId':id})
        account = boto3.session.Session(profile_name='XXXXX', region_name='eu-west-1') # Session = connect to a specific account.
        client = account.client('guardduty')
        response = client.create_members(AccountDetails=list_of_dicts, DetectorId='XXXXX')


      def create_detector(): #enables guardduty detector

        with open('failed_accounts.txt','w'): pass # makes the file empty for each run
        with open('last_file_accounts_a.txt') as accounts: # Reads accounts = id,name
            NameColumn = [line.split(',')[1] for line in accounts] # Reads only name
            print ''
            count = 0
            for name in NameColumn:
                try:
                    name = name.strip('\r\n')
                    account = boto3.session.Session(profile_name=name, region_name='eu-west-1') # Session = connect to a specific account.
                    client = account.client('guardduty')
                    detector_dict = client.list_detectors()
                    detector = detector_dict["DetectorIds"]
                    try:
                        if detector:
                            response = client.delete_detector(DetectorId=detector[0])
                            print name + " - Now is Detector free"
                        response = client.create_detector(Enable=True)
                        print name + " - GuardDuty is now Enabled."
                        print ''
                    except Exception as e:
                        print e
                except Exception as e:
                    print e


      def disassociate_master(): #if account already has a master - disassociate

        with open('last_file_accounts_a.txt') as accounts: # Reads accounts = id,name
            NameColumn = [line.split(',')[1] for line in accounts] # Reads only name
            print ''
            for name in NameColumn:
                name = name.strip('\r\n')
                try:
                    account = boto3.session.Session(profile_name=name, region_name='eu-west-1') # Session = Account name
                    client = account.client('guardduty')
                    detector_id = client.list_detectors()
                    detector_id = detector_id['DetectorIds'][0]
                    response = client.disassociate_from_master_account(DetectorId=detector_id)
                    print name + ' Is now master free'
                except Exception as e:
                    print name + ' had an error:'
                    print e


      def invite_members(): # read from file and create a list of ids ('invite members' only accepts lists). from master profile invite all accounts

        account = boto3.session.Session(profile_name='XXXXXmaster', region_name='eu-west-1') # Session = Master account
        client = account.client('guardduty')
        list_of_ids1=[]
        list_of_ids2=[]
        with open('last_file_accounts_a.txt') as accounts: # Reads accounts = name,email,id
            IdColumn = [line.split(',')[0] for line in accounts] # Reads only ids
            for id in IdColumn:
                id = id.strip('\r\n')

            ListA = IdColumn[:len(IdColumn)//2]
            ListB = IdColumn[len(IdColumn)//2:]

        print ''
        try:
            response1 = client.invite_members(AccountIds=ListB, DetectorId='masterid', DisableEmailNotification=True) # Detector ID belongs to masterid
            response2 = client.invite_members(AccountIds=ListA, DetectorId='masterid', DisableEmailNotification=True) # Detector ID belongs to masterid

        except Exception as e:
            print e


      def accept_invitation(): #from each account, accept

        with open('failed_accounts.txt','w'): pass # makes the file empty for each run
        with open('last_file_accounts_a.txt') as accounts: # Reads accounts = name,email,id
            NameColumn = [line.split(',')[1] for line in accounts] # Reads only names
            print ''
            for name in NameColumn:
                name = name.strip('\r\n')
                account = boto3.session.Session(profile_name=name, region_name='eu-west-1') # Session = Account name
                client = account.client('guardduty')
                try:
                    detector_id = client.list_detectors()
                    detector_id = detector_id['DetectorIds'][0]

                    invitation_id_json = client.list_invitations()
                    for i in invitation_id_json['Invitations']:
                        if i['AccountId'] == 'XXXXX': # if the invitision is from masterid - accept. else - pass.
                            invitation_id = i['InvitationId']
                            response = client.accept_invitation(DetectorId=detector_id,InvitationId=invitation_id,MasterId='XXXXX')
                            print name + ' - Invitation was Accepted!'

                except Exception as e:
                    print e
                    with open('failed_accounts.txt', 'a') as failed_accounts:
                        writer = csv.writer(failed_accounts)
                        writer.writerow([name])


      def fails_print():

        with open ('failed_accounts.txt', 'r') as file:
            print ''
            print 'Failed accounts:'
            print ''
            for name in file:
                print name



      def run():
        #creates and merges list, to be used in the logic process
        list_accounts_from_parent()
        list_accounts_from_file()
        merge_two_lists_a()
        merge_two_lists_b()

        #logic
        create_member()
        create_detector()
        disassociate_master()
        invite_members()
        accept_invitation()
        fails_print()

      run()

def main():

    loop()

main()

