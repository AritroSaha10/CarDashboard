# Car Dashboard
Meant for Raspberry Pis

## Setup
1. Install all requirements
2. Run `sudo ln -s <PATH>/car_dashboard.service /etc/systemd/system/car_dashboard.service`
3. Turn on the service: `sudo systemctl start car_dashboard.service`
4. Check if it works using `sudo systemctl status car_dashboard.service`
5. If it does, enable it to run on boot: `sudo systemctl enable car_dashboard.service`
