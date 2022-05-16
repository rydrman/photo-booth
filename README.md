# Photo Booth

## Running

```sh
# no virtual env or anything, everything is installed
python3 -m photo_booth
```

## Print Setup

```sh
# check that the 'selphy' printer is listed
lpstat -p -d
# if not, try rebooting the cups server
sudo systemctl restart cups
# or re-adding the printer via the web interface 
xdg-open http://localhost:8000
```