#!/bin/bash

############################################################
ROOT_UID=0     # Only users with $UID 0 have root privileges.
E_XCD=86       # Can't change directory?
E_NOTROOT=87   # Non-root exit error.
#############################################################
REGION='eu-west-1'
AWS_PROFILES=profiles.txt
ACCOUNTS_LIST=~/.aws/config
ROLES_FILE=roles.txt
> sts_create_output.txt

function profile {
  cat $ACCOUNTS_LIST | egrep '\[([^]]+)\]' | cut -d '[' -f2 | cut -d ']' -f1 | awk '{print $2}' > $AWS_PROFILES
}

#profile

function cmd {
account=$(/usr/local/bin/aws sts get-caller-identity --query "Account" --profile $LINE --region $REGION --output text)
echo $account >> sts_create_output.txt

for ROLE in $(cat $ROLES_FILE)
do
    /usr/local/bin/aws iam update-assume-role-policy \
        --role-name $ROLE \
        --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"arn:aws:iam::'$account':saml-provider/NTNET"},"Action":"sts:AssumeRoleWithSAML","Condition":{"StringEquals":{"SAML:aud":"https://signin.aws.amazon.com/saml"}}},{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::AccountID:role/'$ROLE'"},"Action":"sts:AssumeRole"}]}' \
        --profile $LINE

        OUT1=$?


        if [ $OUT1 -eq 0 ] ;then
        echo "Role is updated - '$ROLE'." | tee -a sts_create_output.txt
        else
        echo "Role doesn't update - '$ROLE'." |tee -a sts_create_output.txt
        fi
done
    }


function scan {
for LINE in $(cat $AWS_PROFILES)
do
    echo ""|tee -a sts_create_output.txt
    echo "Account $LINE:"|tee -a sts_create_output.txt
    echo "---------------------"|tee -a sts_create_output.txt
cmd

done
}

scan

exit

