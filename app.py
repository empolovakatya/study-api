from flask import Flask, jsonify, request, redirect
import json
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
import functools

with open('districts.json', 'r', encoding='utf-8') as file:
    districts_json = json.load(file)

with open('streets.json', encoding='utf-8') as file1:
    streets_json = json.load(file1)

with open('volunteers.json', encoding='utf-8') as file2:
    volunteers_json = json.load(file2)

app = Flask(__name__)
app.secret_key = 'KdhisHRt7t69#'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

streets_volunteers_association = db.Table('streets_volunteers',
                                          db.Column('street_id', db.Integer, db.ForeignKey('streets.id')),
                                          db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteers.id')))


class District(db.Model):
    __tablename__ = 'districts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    streets = db.relationship('Street', back_populates='district', cascade='all, delete')
    applications = db.relationship('Application', back_populates='district', cascade='all, delete')

    @property
    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
        }


class Street(db.Model):
    __tablename__ = 'streets'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    district = db.relationship('District', back_populates='streets')
    district_id = db.Column(db.Integer, db.ForeignKey('districts.id'))
    volunteers = db.relationship('Volunteer', secondary=streets_volunteers_association, back_populates='streets')
    applications = db.relationship('Application', back_populates='street')

    @property
    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "district": self.district,
            "district_id": self.district_id,
            "volunteers": self.volunteers,
            "applications": self.applications,
        }


class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    userpic = db.Column(db.String)
    phone = db.Column(db.String)
    streets = db.relationship('Street', secondary=streets_volunteers_association, back_populates='volunteers')
    applications = db.relationship('Application', back_populates='volunteer')

    @property
    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "userpic": self.userpic,
            "phone": self.phone,
            "streets": self.streets,
            "applications": self.applications,
        }


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    district = db.relationship('District', back_populates='applications')
    district_id = db.Column(db.Integer, db.ForeignKey('districts.id'))
    street = db.relationship('Street', back_populates='applications')
    street_id = db.Column(db.Integer, db.ForeignKey('streets.id'))
    volunteer = db.relationship('Volunteer', back_populates='applications')
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'))
    address = db.Column(db.String)
    name = db.Column(db.String)
    surname = db.Column(db.String)
    phone = db.Column(db.String)
    text = db.Column(db.String)

    @property
    def serialize(self):
        return {
            "id": self.id,
            "district": self.district,
            "district_id": self.district_id,
            "street": self.street,
            "street_id": self.street_id,
            "volunteer": self.volunteer,
            "volunteer_id": self.volunteer_id,
            "address": self.address,
            "name": self.name,
            "surname": self.surname,
            "phone": self.phone,
            "text": self.text,
        }


@functools.lru_cache(maxsize=1)
def get_data():
    for item in volunteers_json.values():
        volunteer = Volunteer(
            name=str(item['name']),
            userpic=str(item['userpic']),
            phone=str(item['phone']),
        )
        db.session.add(volunteer)
    db.session.commit()
    for i in streets_json.values():
        title = str(i['title'])
        volunteers = []
        for j in i['volunteer']:
            volunteer = db.session.query(Volunteer).filter_by(id=j).first()
            volunteers.append(volunteer)
        street = Street(title=title,
                        volunteers=volunteers)
        db.session.add(street)
    db.session.commit()
    for n in districts_json.values():
        title = str(n['title'])
        streets = []
        for m in n['streets']:
            street = db.session.query(Street).filter_by(id=m).first()
            streets.append(street)
        district = District(title=title, streets=streets)
        db.session.add(district)
    db.session.commit()


if db.session.query(Volunteer).filter_by(id=1).first() == None:
    get_data()


@app.route('/')
def hello_world():
    return redirect('/districts/')


@app.route('/districts/', methods=['GET'])
def districts_func():
    districts_query = District.query.all()
    return (jsonify([i.serialize for i in districts_query]))


@app.route('/streets/', methods=['GET'])
def street_def():
    district_request = request.args.get("district")
    streets = db.session.query(Street)
    if district_request:
        streets = streets.filter(Street.district_id == district_request).all()
    streets_list = []
    for street in streets:
        volunteers = []
        for volunteer in street.volunteers:
            volunteers.append(volunteer.id)
        streets_list.append(
            dict(id=street.id, title=street.title, volunteer=volunteers))
    return jsonify(streets_list)


@app.route('/volunteers/', methods=['GET'])
def volunteers_def():
    streets_request = request.args.get("streets")
    volunteers = db.session.query(Volunteer).all()
    if streets_request:
        id_list = []
        for volunteer in volunteers:
            for street in volunteer.streets:
                if street.id == int(streets_request):
                    id_list.append(volunteer.id)
        volunteers_with_id_list = []
        for idd in id_list:
            volunteers_with_id = db.session.query(Volunteer).filter(Volunteer.id == idd).first()
            volunteers_with_id_list.append(volunteers_with_id)
    volunteer_list = []
    for volunteer in volunteers_with_id_list:
        volunteer_list.append(
            dict(id=volunteer.id, name=volunteer.name, userpic=volunteer.userpic, phone=volunteer.phone)
        )
    return jsonify(volunteer_list)


@app.route('/helpme/', methods=['POST'])
def helpme():
    data = request.get_json()
    application = Application(
        district_id=int(data.get('district')),
        street_id=int(data.get('street')),
        volunteer_id=int(data.get('volunteer')),
        address=data.get('address'),
        name=data.get('name'),
        surname=data.get('surname'),
        phone=data.get('phone'),
        text=data.get('text')
    )
    db.session.add(application)
    db.session.commit()

    return jsonify({
        "status": "success"}), 201


if __name__ == '__main__':
    app.run()
