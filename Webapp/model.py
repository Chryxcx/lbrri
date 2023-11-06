from flask_login import UserMixin

class Librarian(UserMixin):
    def __init__(self, id, email, firstname, lastname, lib_id, lib_pass):
        self.id = id
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.lib_id = lib_id
        self.lib_pass = lib_pass

    def get_id(self):
        return str(self.id)
    

class Admin(UserMixin):
    def __init__(self, id, admin_usr, admin_pass):
        self.id = id
        self.admin_usr=admin_usr
        self.admin_pass=admin_pass


    def get_id(self):
        return str(self.id)