from app import create_app


app = create_app(debug=False)
server = app.server
