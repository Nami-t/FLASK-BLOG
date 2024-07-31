from index import create_app
from index import db

app=  create_app()


'''if __name__=="__main__":
    app.run(debug=True)'''

@app.route('/')
def home():
    return "Hello, World!"


with app.app_context():
    db.create_all()    