# Village Vault - Village Banking APplication

This is a web application for managing a village banking system, which allows users to invest money, borrow money, and earn interest. The application is built using Python Flask and several Flask extensions, including Flask-Login for authentication, Flask-Mail and itsdangerous library for email token generation, SQL Alchemy as the ORM, and Flask Forms for form generation.

## Features

User registration and authentication with Flask-Login
Investment cycles with set interest rates and returns
Lending cycles with set interest rates and penalties for late payments
Email notifications for password resets and other sensitive operations with Flask-Mail and itsdangerous library
Secure user authentication and session management with Flask-Login
User interface generated with Flask Forms
Getting Started
To run the application, you will need to install Python 3 and several Python packages. First, clone this repository to your local machine:

bash
Copy code
git clone https://github.com/shizoe/VILLAGE_VAULT.git
Next, navigate to the project directory and create a virtual environment:

bash
Copy code
cd VILLAGE_VAULT
python3 -m venv venv
Activate the virtual environment:

bash
Copy code
source venv/bin/activate
Install the required packages:

Copy code
pip install -r requirements.txt
Finally, run the application:

arduino
Copy code
flask run
The application should now be accessible at http://localhost:5000.

## Contributing
If you would like to contribute to the project, please fork the repository and submit a pull request with your changes.

## License


## Acknowledgments

Flask documentation
Flask-Login documentation
Flask-Mail documentation
itsdangerous library documentation
SQL Alchemy documentation
Flask Forms documentation

## Support

If you encounter any issues or have any questions, please feel free to contact us at mabombebeta@gmail.com.




