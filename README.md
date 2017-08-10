[![Build status](https://travis-ci.org/City-of-Helsinki/tunnistamo.svg)](https://travis-ci.org/City-of-Helsinki/tunnistamo)
[![codecov](https://codecov.io/gh/City-of-Helsinki/tunnistamo/branch/master/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/tunnistamo)
[![Requirements](https://requires.io/github/City-of-Helsinki/tunnistamo/requirements.svg?branch=master)](https://requires.io/github/City-of-Helsinki/tunnistamo/requirements/?branch=master)

# Tunnistamo

## Prerequisites

Tunnistamo runs on postresql. Install the server on Debian based systems with:
```
apt install postgresql
```

Then create a postgres user and db as root:
```
createuser <your username>
createdb -O <your username> tunnistamo
```


## Installing
Clone the repo:
```
git clone https://github.com/City-of-Helsinki/tunnistamo.git
cd tunnistamo
```

Initiate a virtualenv and install the Python requirements:
```
pyenv virtualenv tunnistamo-env
pyenv local tunnistamo-env
pip install -r requirements.txt
```

Create `local_settings.py` in the repo base dir containing the following line:
```
DEBUG = True
```

Run migrations:
```
python manage.py migrate
```

Create admin user:
```
python manage.py createsuperuser
```

Run dev server:
```
python manage.py runserver
```
and login to http://127.0.0.1:8000/ using the admin user credentials.

## Developing

### Outdated Python dependencies
Tunnistamo uses [prequ](https://github.com/suutari/prequ) – a fork of pip-tools –
to manage the Python dependencies.
prequ can handle `-e` style dependencies (git URLs) in the requirements files.
 
Update the requirements with:
```
pip install prequ
rm requirements.txt
prequ update
```

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
