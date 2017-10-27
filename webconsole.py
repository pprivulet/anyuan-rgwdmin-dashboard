#!/usr/bin/env python


import bcrypt
import concurrent.futures


import os.path
import re
import subprocess
import torndb
import tornado.escape
from tornado import gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="ceph web console database host")
define("mysql_database", default="ceph_web_console", help="ceph web console database name")
define("mysql_user", default="webconsole", help="ceph web console database user")
define("mysql_password", default="webconsole1234", help="webconsole database password")


# A thread pool to be used for password hashing with bcrypt.
executor = concurrent.futures.ThreadPoolExecutor(2)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            #(r"/archive", ArchiveHandler),
            #(r"/feed", FeedHandler),
            #(r"/entry/([^/]+)", EntryHandler),
            (r"/generate", GenerateHandler),
            (r"/user/create", UserCreateHandler),
            (r"/user/login", UserLoginHandler),
            (r"/user/logout", UserLogoutHandler),
            (r"/userMgm", UserMgmHandler),

        ]
        settings = dict(
            app_title=u"Ceph web console",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            #ui_modules={"Entry": EntryModule},
            xsrf_cookies=True,
            cookie_secret="anyuan#ceph*web!console",
            login_url="/user/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)
  

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("web_console_user")
        if not user_id: return None
        return self.db.get("SELECT * FROM users WHERE id = %s", int(user_id))

    def any_user_exists(self):
        return bool(self.db.get("SELECT * FROM users LIMIT 1"))



class UserMgmHandler(BaseHandler):
    def get(self):
        user = self.get_current_user() 
        print user        
        self.render("index.html", user=user)



class HomeHandler(BaseHandler):
    def get(self):
        apps = self.db.query("SELECT * FROM applications ORDER BY published "
                                "DESC LIMIT 5")
        if not apps:
            self.redirect("/generate")
            return
        self.render("home.html", apps=apps)


class AppHandler(BaseHandler):
    def get(self):
        app = self.db.get("SELECT * FROM applications WHERE id = %s", int(id))
        if not entry: raise tornado.web.HTTPError(404)
        self.render("app.html", app=app)

'''
class ArchiveHandler(BaseHandler):
    def get(self):
        entries = self.db.query("SELECT * FROM entries ORDER BY published "
                                "DESC")
        self.render("archive.html", entries=entries)


class FeedHandler(BaseHandler):
    def get(self):
        entries = self.db.query("SELECT * FROM entries ORDER BY published "
                                "DESC LIMIT 10")
        self.set_header("Content-Type", "application/atom+xml")
        self.render("feed.xml", entries=entries)
'''

class GenerateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        app = None
        if id:
            app = self.db.get("SELECT * FROM applications WHERE id = %s", int(id))
        self.render("generate.html", app=app)

    @tornado.web.authenticated
    def post(self):
        self.write("TODO")
        '''
        id = self.get_argument("id", None)
        title = self.get_argument("title")
        text = self.get_argument("markdown")
        html = markdown.markdown(text)
        if id:
            entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(id))
            if not entry: raise tornado.web.HTTPError(404)
            slug = entry.slug
            self.db.execute(
                "UPDATE entries SET title = %s, markdown = %s, html = %s "
                "WHERE id = %s", title, text, html, int(id))
        else:
            slug = unicodedata.normalize("NFKD", title).encode(
                "ascii", "ignore")
            slug = re.sub(r"[^\w]+", " ", slug)
            slug = "-".join(slug.lower().strip().split())
            if not slug: slug = "entry"
            while True:
                e = self.db.get("SELECT * FROM entries WHERE slug = %s", slug)
                if not e: break
                slug += "-2"
            self.db.execute(
                "INSERT INTO entries (author_id,title,slug,markdown,html,"
                "published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
                self.current_user.id, title, slug, text, html)
        self.redirect("/entry/" + slug)
        '''

class UserCreateHandler(BaseHandler):
    def get(self):
        self.render("create_user.html")

    @gen.coroutine
    def post(self):
        if self.any_user_exists():
            raise tornado.web.HTTPError(400, "user already created")
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            bcrypt.gensalt())
        user_id = self.db.execute(
            "INSERT INTO users (email, name, hashed_password) "
            "VALUES (%s, %s, %s)",
            self.get_argument("email"), self.get_argument("name"),
            hashed_password)
        self.set_secure_cookie("web_console_user", str(user_id))
        self.redirect(self.get_argument("next", "/"))


class UserLoginHandler(BaseHandler):
    def get(self):
        # If there are no authors, redirect to the account creation page.
        if not self.any_user_exists():
            self.redirect("/user/create")
        else:
            self.render("login.html", error=None)

    @gen.coroutine
    def post(self):
        user = self.db.get("SELECT * FROM users WHERE email = %s",
                             self.get_argument("email"))
        if not user:
            self.render("login.html", error="email not found")
            return
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(user.hashed_password))
        if hashed_password == user.hashed_password:
            self.set_secure_cookie("web_console_user", str(user.id))
            self.redirect(self.get_argument("next", "/"))
        else:
            self.render("login.html", error="incorrect password")


class UserLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("web_console_user")
        self.redirect(self.get_argument("next", "/"))

'''
class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)
'''

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    print "Server running on port:",options.port
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()

