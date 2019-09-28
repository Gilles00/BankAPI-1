from flask import Flask,jsonify,request
from flask_restful import Api,Resource
from pymongo import MongoClient
from flask_pymongo import PyMongo
from flask_cors import CORS
import bcrypt


app = Flask(__name__)
api = Api(app)
CORS(app)


client = PyMongo(app, uri="mongodb://localhost:27017/bank_api")
users = client.db.users
admin = client.db.admin


def user_exists(username):
    if users.find({'username':username}).count()==0:
        return False
    return True;

def invalid_user():
    return generate_return_json('301','Invalid Username')

def incorrect_password():
    return generate_return_json('302','Incorrect password')

def insufficient_balance():
    return generate_return_json('304','You are running out of money, please add')

class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        
        if user_exists(username):
            errJson={
                "status":"301",
                "msg":"Invalid username"
            }

            return jsonify(errJson)

        
        password = postedData["password"]

        hashed_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())
        users.insert({
            'username' : username,
            'password' : hashed_pw,
            'own' : 0,
            'debt' : 0
        })

        successJson={
            "status":"200",
            "msg":"You succesfully signed up"
        }

        return jsonify(successJson)

class Login(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        
        if user_exists(username):
            errJson={
                "status":"301",
                "msg":"Invalid username"
            }

            return jsonify(errJson)

        
        password = postedData["password"]

        retJson, error = verify_credentials(username,password)

        if error:
            return jsonify(retJson)
        
        successJson={
            "status":"200",
            "msg":"You succesfully signed up"
        }

        return jsonify(successJson)


def validate_password(username,password):
    if not user_exists(username):
        return False

    hashed_pw = users.find({'username':username})[0]["password"]
    print(hashed_pw)
    if bcrypt.hashpw(password.encode('utf8'),hashed_pw) == hashed_pw:
        return True

    return False

def user_cash(username):
    cash = users.find({'username':username})[0]["own"]
    return cash

def user_debt(username):
    debt = users.find({'username':username})[0]["debt"]
    return debt

def generate_return_json(status,msg):
    dictJson = {
        'status':status,
        'msg':msg
    }

    return dictJson

def verify_credentials(username,password):
    if not user_exists(username):
        return invalid_user(),True
    
    correct_pw = validate_password(username,password)
    if not correct_pw:
        return incorrect_password(), True

    return None, False

def update_cash(username,balance):
    users.update({'username':username},{"$set":{'own':balance}})

def update_debt(username,balance):
    users.update({'username':username},{"$set":{'debt':balance}})

class Add(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        retJson,error = verify_credentials(username,password)
        if error:
            return jsonify(retJson)

        money = postedData["amount"]

        if money<=0:
            return jsonify(generate_return_json('304','The money amount must be greater than 0'))

        cash = user_cash(username)
        bank_cash = user_cash("BANK")
        charge = money*0.001
        money=money-charge
        update_cash("BANK",bank_cash+charge)
        update_cash(username,cash+money)

        return jsonify(generate_return_json('200','Money added succesfully'))

class Transfer(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verify_credentials(username,password)

        if error:
            return jsonify(retJson)

        to = postedData["to"]
        money = postedData["amount"]

        cash = user_cash(username)
        if cash < money:
            return jsonify(insufficient_balance())

        if not user_exists(to):
            return jsonify(invalid_user())
        
        cash_from = user_cash(username)
        cash_to = user_cash(to)
        cash_bank = user_cash("BANK")

        update_cash("BANK",cash_bank+2)
        update_cash(username,cash_from-money-1)
        update_cash(to,cash_to+money-1)

        return jsonify(generate_return_json(200,"Money transfered succesfully"))

class Balance(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verify_credentials(username,password)

        if error:
            return jsonify(retJson)

        retJson = users.find({'username':username},{'_id':0,'password':0})[0]

        return jsonify(retJson)

class TakeLoan(Resource):
    def post(self):
        print("Take loan")
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verify_credentials(username,password)

        if error :
            return jsonify(retJson)

        money = postedData["amount"]
        bank_cash = user_cash("BANK")

        if bank_cash-money < 20000000000:
            return jsonify(generate_return_json('304','Sorry, Bank can not provide loan of that much amount'))
        cash = user_cash(username)
        debt = user_debt(username)
        update_cash(username,cash+money)
        update_debt(username,debt+money)
        update_cash("BANK",bank_cash-money)

        return jsonify(generate_return_json('200','Loan added to your account'))




class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData['username']
        password = postedData['password']

        retJson, error = verify_credentials(username,password)
        if error:
            return jsonify(retJson)

        money = postedData['amount']
        cash = user_cash(username)
        debt = user_debt(username)
        new_cash = cash-money
        new_debt = debt-money
        if new_cash < 0:
            return jsonify(insufficient_balance())

        if new_debt < 0:
            return jsonify(generate_return_json('304','You are paying extra'))

        bank_cash = user_cash("BANK")

        update_cash(username,new_cash) 
        update_debt(username,new_debt)
        update_cash("BANK",bank_cash+money)

        return jsonify(generate_return_json('200','You paid your debt succesfully'))

class Test(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData['username']
        password = postedData['password']
        retJson, error = verify_credentials(username,password)

        print(retJson)
        if error:
            return jsonify({'data' : retJson, 'validate' : False})
        
        return jsonify({'validate': True})
        
api.add_resource(Register,'/register')
api.add_resource(Add,'/add')
api.add_resource(Transfer,'/transfer')
api.add_resource(Balance,'/balance')
api.add_resource(TakeLoan,'/loan/take')
api.add_resource(PayLoan,'/loan/pay')
api.add_resource(Test,'/test')

        


