sudo apt-get update
sudo apt install python3 python3-tk
sudo apt-get install python3-openpyxl
sudo rm -rf LCD-show

git clone https://github.com/goodtft/LCD-show.git
chmod -R 755 LCD-show

sudo systemctl daemon-reload
sudo systemctl enable startup.service
sudo systemctl start startup.service

echo "
Dependências instaladas..."
