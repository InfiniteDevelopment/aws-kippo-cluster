#!/bin/sh

# Assign script arguments to variables
RDS_HOST=$1
RDS_ROOT_PASSWORD=$2
REAL_SSH_PORT=$3

# Define constants
KIPPO_DB_PASSWORD=8e55a8a4e47fc64ac783a8d3924653c8

# Update system packages
/usr/bin/apt-get update
/usr/bin/apt-get upgrade -y

# Change the SSH port to $REAL_SSH_PORT
/bin/sed -i "s/Port 22/Port ${REAL_SSH_PORT}/" /etc/ssh/sshd_config
/usr/sbin/service ssh restart

# Clone a copy of kippo
/usr/bin/apt-get install -y git
/usr/bin/git clone https://github.com/desaster/kippo.git /opt/kippo

# Create a non-privileged user to run kippo under and have them own the kippo
# application files
/usr/sbin/useradd kippo
/bin/chown -R kippo.kippo /opt/kippo

# Set up the kippo database schema, if it has not already been set up
/usr/bin/apt-get install -y mysql-client
/usr/bin/mysql -h ${RDS_HOST} -uroot -p${RDS_ROOT_PASSWORD} -e 'USE kippo'
if (($? != 0)); then
    /usr/bin/mysql -h ${RDS_HOST} -uroot -p${RDS_ROOT_PASSWORD} -e 'CREATE DATABASE kippo'
    /usr/bin/mysql -h ${RDS_HOST} -uroot -p${RDS_ROOT_PASSWORD} kippo < /opt/kippo/doc/sql/mysql.sql
    /usr/bin/mysql -h ${RDS_HOST} -uroot -p${RDS_ROOT_PASSWORD} -e "GRANT ALL ON kippo.* TO kippo@\"%\" IDENTIFIED BY \"${KIPPO_DB_PASSWORD}\""
fi

# Configure kippo
cp /opt/kippo/kippo.cfg.dist /opt/kippo/kippo.cfg
/bin/sed -i 's/#\[database_mysql\]/[database_mysql]/' /opt/kippo/kippo.cfg
/bin/sed -i "s/#host = localhost/host = ${RDS_HOST}/" /opt/kippo/kippo.cfg
/bin/sed -i "s/#database = kippo/database = kippo/" /opt/kippo/kippo.cfg
/bin/sed -i "s/#username = kippo/username = kippo/" /opt/kippo/kippo.cfg
/bin/sed -i "s/#password = secret/password = ${KIPPO_DB_PASSWORD}/" /opt/kippo/kippo.cfg
/bin/sed -i "s/#port = 3306/port = 3306/" /opt/kippo/kippo.cfg

# Install kippo dependancies and run kippo
/usr/bin/apt-get install -y build-essential python-dev libmysqlclient-dev python-virtualenv python-pip
/usr/bin/pip install twisted pyasn1 pycrypto MySQL-python
sudo -u kippo /opt/kippo/start.sh

# /usr/bin/apt-get install -y build-essential python-dev libmysqlclient-dev python-virtualenv python-pip
# cd /opt/kippo
# /usr/bin/virtualenv env
# source ./env/bin/activate
# /usr/bin/pip install twisted
# /usr/bin/pip install pyasn1
# /usr/bin/pip install pycrypto
# /usr/bin/pip install MySQL-python
# sudo -u kippo ./start.sh env

# Forward port 22 to kippo
/usr/bin/apt-get install -y iptables-persistent
/sbin/iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222
/sbin/iptables-save > /etc/iptables/rules.v4

# Install and configure kippo-graph
/usr/bin/apt-get install -y apache2 libapache2-mod-php5 php5-mysql php5-gd php5-curl
cd /var/www/html
/usr/bin/git clone https://github.com/ikoniaris/kippo-graph.git
cd kippo-graph
/bin/chmod 777 generated-graphs
/bin/cp config.php.dist config.php
/bin/sed -i "s/define('DB_HOST', '127.0.0.1');/define('DB_HOST', '${RDS_HOST}');/" /var/www/html/kippo-graph/config.php
/bin/sed -i "s/define('DB_USER', 'username');/define('DB_USER', 'kippo');/" /var/www/html/kippo-graph/config.php
/bin/sed -i "s/define('DB_PASS', 'password');/define('DB_PASS', '8e55a8a4e47fc64ac783a8d3924653c8');/" /var/www/html/kippo-graph/config.php
/bin/sed -i "s/define('DB_NAME', 'database');/define('DB_NAME', 'kippo');/" /var/www/html/kippo-graph/config.php
/usr/sbin/service apache2 restart
