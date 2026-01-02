# Cronjob

# 1. Open following
sudo crontab -e

# 2. Cron line ( will execute on every monday)
0 2 * * 1 /usr/bin/python3 /home/<username>/scripts/tb_edge_backup.py >> /var/log/tb_edge_backup.log 2>&1



# 3. directory permission
sudo mkdir -p /home/energenix/scripts
sudo chmod 755 /home/energenix/scripts


