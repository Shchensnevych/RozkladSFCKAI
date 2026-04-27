# -*- coding: utf-8 -*-
import os
import re
import csv
import json
import logging
import traceback
from datetime import datetime
from os.path import dirname, abspath

# Django HTTP та відповіді
from django.http import (
    Http404, HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.conf.urls.static import static

# Django модулі утиліт
from django.utils.html import escape
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_protect
from django.middleware import csrf
from django.views.decorators.http import require_GET

# Django шаблони
from django.template import loader
from django.template.loader import render_to_string
from django.template.context_processors import request
from django.template.exceptions import TemplateDoesNotExist

# Django ORM та транзакції
from django.db import connections, transaction
from django.db.models import Q, Count

# Django автентифікація та сайти
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Permission, User, Group
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.admin.views.decorators import staff_member_required


# Ваші моделі
from .models import Navigation, Article, Comment, Vip, Album, Photo, Tag, Timetable, PhotoAlbum

# Ваші утиліти та модулі
from .page_renderer import getPage, notify
from .utils import get_client_ip, getNavigation, clean_url, build_menu_item
from .breadcrumbs import get_breadcrumbs_from_path
from .tokens import account_activation_token


# Налаштування логування
logger = logging.getLogger(__name__)





@require_GET
def search_navigation(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        matches = Navigation.objects.filter(linktext__icontains=query, is_visible=1).order_by('lft')
        for item in matches:
            node = build_menu_item(item, only_visible=False, include_children=False)
            if node:
                node["parents"] = [p.id for p in item.get_ancestors()]
                node["path"] = " / ".join([p.linktext for p in item.get_ancestors()] + [item.linktext])
                node["level"] = item.level  # ← важливо для CSS-класу depth-X
                results.append(node)

    return JsonResponse({'results': results})



@require_GET
def load_menu_children(request, parent_id):
    try:
        parent = Navigation.objects.get(id=parent_id)
        children_data = []

        for child in parent.get_children().filter(is_visible=1).order_by('lft'):
            child_data = build_menu_item(child, only_visible=True, include_children=False)
            if child_data:
                children_data.append(child_data)

        return JsonResponse({'children': children_data})
    except Navigation.DoesNotExist:
        return JsonResponse({'children': []})


def build_menu_tree(navigation_items):
    """
    Побудова дерева з об'єктів Navigation із оновленими URL.
    """
    for item in navigation_items:
        item.url = clean_url(item.link, item.linktype) or "#"

    menu_dict = {item.id: {"item": item, "children": []} for item in navigation_items}
    menu_tree = {}

    for item in navigation_items:
        if item.parent and item.parent.id in menu_dict:
            menu_dict[item.parent.id]["children"].append(menu_dict[item.id])
        else:
            menu_tree[item.id] = menu_dict[item.id]

    return menu_tree


def site_map(request):
    navigation_items = Navigation.objects.filter(is_visible=1).order_by('tree_id', 'lft')
    menu_tree = build_menu_tree(navigation_items)
    return getPage(request, 'sitemap.html', {
        'menu_tree': menu_tree,
        'breadcrumbs': [{'text': 'Карта сайту', 'url': '/sitemap/'}],
    })




def resume_view(request):
    # Фільтрація: тільки новини з валідними зображеннями
    latest_articles = Article.objects.filter(
        ~Q(title_logo_link__in=["", "#", "None", None]) &
        ~Q(title_logo_link__icontains="news_placeholder.webp")
    ).order_by('-pub_date')[:4]

    context = {
        'dynamic_slides': latest_articles,
    }
    return getPage(request, 'resume.html', context)



def page_not_found_view(request, exception):
    return getPage(request, '404.html', status=404)



def StartPage(request):
    try:
        return resume_view(request)
        #return getPage(request,'resume.html')
    except Exception as ex:
        print(repr(ex))



def getNews(request, article_id=1):
    try:
        latest_articles_list = Article.objects.order_by('-is_pinned', '-pub_date')
        paginator = Paginator(latest_articles_list, 12)
        posts = paginator.page(article_id)

        breadcrumbs = [
            {'text': 'Новини', 'url': '/news/'},
        ]

        data = {
            'posts': posts,
            'range': range(1, posts.paginator.num_pages + 1),
            'sub': '/news/page=',
            'user_is_teacher': request.user.groups.all().filter(name='Teacher').exists(),
            'breadcrumbs': breadcrumbs,
        }
        return getPage(request, 'list.html', data)
    except Exception as ex:
        print(repr(ex))
        return getPage(request, '404.html')


def get_Articles(request, article_id=1):
    if article_id == 1:
        return redirect('/news')

    try:
        page = article_id
        latest_articles_list = Article.objects.order_by('-pub_date')
        paginator = Paginator(latest_articles_list, 5)
        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts = paginator.page(1)
        except EmptyPage:
            posts = paginator.page(paginator.num_pages)
        data = {
            'page': page,
            'posts': posts
        }
        return getPage(request, 'list.html', data)
    except Exception as ex:
        print(repr(ex))




def getArticles(request):
    latest_articles_list = Article.objects.order_by('-pub_date')[:5]
    articles = []

    for a in latest_articles_list:
        articles.append({
            'title': escape(a.title),
            'detail_link': a.detail_link
        })

    return JsonResponse({'articles': articles})



def detail(request, article_id=None):
    try:
        a = Article.objects.get(id=article_id)
    except:
        raise Http404('page not found')

    latest_comments_list = a.comment_set.order_by('-id')

    breadcrumbs = [
        {'text': 'Новини', 'url': '/news/'},
        {'text': a.title, 'url': f'/detail/{a.id}/'},
    ]

    data = {
        'article': a,
        'latest_comments_list': latest_comments_list,
        'csrf_token': csrf.get_token(request),
        'user': request.user,
        'breadcrumbs': breadcrumbs,
    }

    return getPage(request, 'detail.html', data)

def new_comments(request, article_id = None):
    try:
        try:
            a = Article.objects.get(id = article_id)
        except:
            raise Http404('сторінка не знайдена...')

        comment = request.POST['comment']
        a.comment_set.create(author_name = request.user.get_full_name(),comment_text = comment)

        return redirect(f'/detail/{article_id}')
    except Exception as ex:
        print(ex)



    #return HttpResponseRedirect(reverse('scnau:detail', args=(a.id,) ))


def leave_comment(request):
    print('yep')
    uid = request.POST['uid']
    try:
        a = Article.objects.get(id = uid)
    except:
        raise Http404('page not found')

    a.comment_set.create(author_name = request.POST['name'],comment_text = request.POST['text'])

    try:
        a = Article.objects.get(id = uid)
    except:
        raise Http404('page not found')

    return getPage(request, 'detail.html',{'article' : a,'csrf_token':csrf.get_token(request),})

    #return HttpResponseRedirect(reverse('scnau:detail', args=(a.id,) ))


def makeTimetable(request,path):
    recordset = []
    rec = 0
    s = ""
    path = settings.PROJECT_ROOT + path
    try:
        with open(path, "r", newline="",encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                #recordset.append(row)
                row2 = []
                s += "<p style='text-align: left;'>"
                for e in row:
                    #s += e.decode('cp1252').encode('utf-8') + ","
                    row2.append(e)
                    s += e + ","
                s += "</p>";
                recordset.append(row2)
                s += "<br>";
    except Exception as ex:
        s += "<br>Ошибка при чтении файла с расписанием <br>"

        if hasattr(ex, 'message'):
            s += str(ex.message)
        else:
            s += str(ex)
        s += "<br>"
        html = "<h4>" + path + "</h4><p>" + s  + "</p>"
        return html


    try:
        s += "Очистка расписания..."
        Timetable.objects.all().delete()
        s += "успешно<br>"
        s += "занесение данных..."
        all_pairs = []
        with transaction.atomic():
            for r in recordset:
                date_line = re.findall('\d{4}-\d{2}-\d{2}',r[0])
                t = Timetable.objects.create(dt = date_line[0])
                t.tid = r[1]
                t.fam = r[2]
                t.pair = r[3]
                t.gid = r[4]
                t.gname = r[5]
                t.kod = r[6]
                t.lesson = r[7]
                t.save()
                rec += 1
        s += "успешно<br>"
        print(all_pairs)
        return s
    except Exception as ex:
        s += "<br>Ошибка при работе с расписанием (rec=" + str(rec) + ")<br>"
        for rr in r:
            s += rr + "<br>"

        if hasattr(ex, 'message'):
            s += str(ex.message)
        else:
            s += str(ex)
        s += "<br>"
    html = "<p>" + s  + "</p><h4> " + path + "</h4>"
    return html


def selectTeacher(request):
    t = []
    try:
        tt = Timetable.objects.all().order_by('tid')
        tid = []
        for e in tt:
            if e.tid not in tid:
                t.append(e)
                tid.append(e.tid)
    except Exception as ex:
        err = ''
        if hasattr(ex, 'message'):
            err += str(ex.message)
        else:
            err += str(ex)
        print("oops" + err)
        t = []
    t = sorted(t, key = lambda x: x.fam)
    data = {
        "teach": t,
    }
    return getPage(request, 'tt_teachers.html', data)

def getTeacherTimetable(request, tid=None):
    if tid == None:
        return redirect('/selectTeacher/')
    rs = []
    days = {}
    fam = ""  # додаємо змінну
    weekdays = ['Понеділок','Вівторок','Середа','Четвер','П\'ятниця','Субота','Неділя']

    try:
        rs = list(Timetable.objects.all().filter(tid=tid).order_by('dt', 'pair'))
        if rs:  # якщо є записи
            fam = rs[0].fam  # беремо прізвище з першого запису
            date = rs[0].dt
            day = []
            while len(rs) > 0:
                pair = rs[0]
                group = '| '
                pairs_cont = list(filter(lambda item: pair.dt.date() == item.dt.date() and pair.pair == item.pair, rs))
                while len(pairs_cont) > 0:
                    item = pairs_cont[0]
                    if item in rs:
                        index = rs.index(item)
                        print(f'{index} : {item} ')
                        rs.pop(index)
                    else:
                        group += f'{item.gname} | '
                        pairs_cont.remove(item)
                pair.gname = group
                if pair.dt == date:
                    day.append(pair)
                else:
                    wk = weekdays[date.date().weekday()]
                    days[f'{wk} {date.date().strftime("%d.%m.%Y")}'] = day
                    day = []
                    date = pair.dt
                    day.append(pair)
            wk = weekdays[date.date().weekday()]
            days[f'{wk} {date.date().strftime("%d.%m.%Y")}'] = day
    except Exception as ex:
        print(ex)

    data = {
        "fam": fam,  # додаємо прізвище
        "days": days
    }

    return getPage(request, 'tt_teacher.html', data)

def selectGroup(request):
    g = []
    try:
        gg = Timetable.objects.all().order_by('gid')
        gid = -1
        for e in gg:
            if e.gid != gid:
                g.append(e)
                gid = e.gid

    except Exception as ex:
        err = ''
        if hasattr(ex, 'message'):
            err += str(ex.message)
        else:
            err += str(ex)
        print("oops " + err)
        g = []
    g = sorted(g, key = lambda x: x.gname)
    data = {
        "grp": g,
    }
    return getPage(request, 'tt_groups.html', data)


def getGroupTimetable(request, gid=None):
    if gid == None:
        return redirect('/selectGroup/')
    rs = []
    days = {}
    gname = ""  # додаємо змінну
    weekdays = ['Понеділок','Вівторок','Середа','Четвер','П\'ятниця','Субота','Неділя']

    try:
        rs = Timetable.objects.all().filter(gid=gid).order_by('dt', 'pair')
        if rs.exists():  # перевіряємо чи є записи
            gname = rs[0].gname  # беремо назву групи з першого запису
            date = rs[0].dt
            print(f'{date} - {type(date.date())}')
            day = []
            for pair in rs:
                if pair.dt == date:
                    day.append(pair)
                else:
                    wk = weekdays[date.date().weekday()]
                    days[f'{wk} {date.date().strftime("%d.%m.%Y")}'] = day
                    day = []
                    date = pair.dt
                    day.append(pair)
            wk = weekdays[date.date().weekday()]
            days[f'{wk} {date.date().strftime("%d.%m.%Y")}'] = day
    except Exception as ex:
        print(ex)

    data = {
        "gid": str(gid),
        "gname": gname,  # додаємо назву групи
        "days": days
    }

    return getPage(request, 'tt_group.html', data)



def getTimetableAdmin(request):
    try:
        err = ''
        if not request.user.groups.all().filter(name='Site-manager').exists() and not request.user.is_superuser:
            data = {
                'context' : "<font color='red' size='5em'>Вам не надано доступ, зверніться до адміністратора</font>",
                'user': request.user,
            }
            return getPage(request,'void.html',data)
        else:
            data = {
                'user': request.user,
                'csrf_token' : csrf.get_token(request),
            }
            return getPage(request,'tt_admin_page.html',data)
    except Exception as ex:
        print(repr(ex))



def simple_upload(request):
    err = ''
    if request.method == 'POST' and request.FILES['tt_file']:
        tt_file = request.FILES['tt_file']

        fs = FileSystemStorage()
        date = datetime.strptime(str(datetime.now().date()), "%Y-%m-%d")
        path_to_file = f'timetable/{date.year}/{date.month}/{date.day}/{tt_file.name}'
        if os.path.exists(path_to_file):
            print(path_to_file)
        else:
            filename = fs.save(path_to_file, tt_file)
            uploaded_file_url = fs.url(filename)

            context = loader.render_to_string('simple_upload.html',{'uploaded_file_url': uploaded_file_url,}) + '<br>'
            context += makeTimetable(request,uploaded_file_url)

            return getPage(request,'void.html',{'context': context})

    html = "<h4> Помилка завантаження </h4><p> Спробуйте завантажити через FTP </p>"
    return getPage(request,'void.html',{'context':html,})

def get_Albums(request):
    return redirect('/albums/')



def get_Albums2(request, page=1):
    albums_list = Album.objects.annotate(photo_count=Count('photo')).order_by('order')

    # Додаємо колір рамки та рідкість
    for album in albums_list:
        if album.photo_count <= 5:
            album.color_class = "album-border-green"
            album.rarity = "Common Album"
        elif album.photo_count <= 10:
            album.color_class = "album-border-blue"
            album.rarity = "Rare Album"
        else:
            album.color_class = "album-border-purple"
            album.rarity = "Epic Album"

    paginator = Paginator(albums_list, 12)

    if not isinstance(page, int):
        try:
            page = int(page.split('=')[1])
        except:
            page = 1

    if page < 1:
        page = 1

    if page > paginator.num_pages:
        return redirect(f'/albums/page={paginator.num_pages}/')

    posts = paginator.page(page)

    return getPage(request, 'albums2.html', {
        "posts": posts,
        "range": range(1, paginator.num_pages + 1),
        "sub": '/albums/page=',
        "breadcrumbs": [
            {'text': 'Фотоальбоми', 'url': '/albums/'},
        ]
    })



from .models import PhotoAlbum

def getPhotos(request, album_id=1, page=None):
    if page is None:
        return redirect(f'/photos/{album_id}/page=1/')

    try:
        album = Album.objects.get(id=album_id)
        album_name = album.title
    except Album.DoesNotExist:
        album_name = '?'

    # Отримуємо зв'язки з порядком у альбомі
    photoalbums_qs = PhotoAlbum.objects.filter(album_id=album_id).select_related('photo').order_by('order')

    # Дістаємо фото з кожного PhotoAlbum
    photos_ordered = [pa.photo for pa in photoalbums_qs]

    paginator = Paginator(photos_ordered, 20)

    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return getPage(request, 'photos.html', {
        'page': page,
        'album_name': album_name,
        'album_id': album_id,
        'range': range(1, posts.paginator.num_pages + 1),
        'sub': f'/photos/{album_id}/page=',
        "posts": posts,
        "breadcrumbs": [
            {'text': 'Фотоальбоми', 'url': '/albums/'},
            {'text': album_name, 'url': f'/photos/{album_id}/page=1/'},
        ]
    })


def login_page(request):
    return getPage(request,"login.html",{"user":request.user})

def authUser(request):
    try:
        data_request = json.dumps(request.POST)
        login_user = request.POST['user_login']
        password_cash = request.POST['user_pass']
        password_user = ''
        for code in password_cash.encode('ascii'):
            code -=7
            password_user +=chr(code)

        messageauth = ''
        user = authenticate(username=login_user, password=password_user)
        user_data = {}
        if user is not None:
            # print(user.groups.filter(name='Teacher').exists()) Учитель
            User.objects.filter(pk=user.pk).update(last_login=datetime.now())
            login(request,user)
            user_data = {
                'success' : True,
                'user_login' : user.get_username(),
                'user_name' : user.get_full_name(),
                'user_time_login' : datetime.now()
            }
        else:
            user_data = {
                'success' : False,
                'message' : 'Користувач або пароль введено невірно!'
            }

        data_response = json.dumps(user_data,indent=4,sort_keys=True,default=str)
        return HttpResponse(data_response)
    except Exception as ex:
        print(ex)





def logout_func(request):
    if request.user.is_authenticated:
        user_full_name = request.user.get_full_name()
    else:
        user_full_name = "Anonymous"
    logout(request)
    return redirect('/')





def registration(request):
    err =""
    status = True
    try:
        if request.method == "POST":
            username = request.POST["login"]
            password = request.POST["password"]
            retpassword = request.POST["retpassword"]
            email = request.POST["email"]
            name = request.POST["name"]
            family = request.POST["family"]

            if password != retpassword:
                err += "Паролі не співпадають\n"
                status = False
            elif len(User.objects.all().filter(username = username)) == 0 and len(User.objects.all().filter(email = email)) == 0:
                if name.lstrip().rstrip() == None or family.lstrip().rstrip() == None:
                    err = "Введіть призвище та ім'я"
                    status = False
                else:
                    user = User.objects.create_user(username=username,password=password)
                    user.first_name = name
                    user.last_name = family
                    user.email = email
                    group = Group.objects.get(name='Student')
                    group_all = Group.objects.get(name='All_users')
                    group.user_set.add(user)
                    group_all.user_set.add(user)
                    user.is_active = False
                    user.save()

                    # Send token email
                    message = loader.render_to_string('email_verify.html', {
                        'user': user,
                        'domain': 'sfknau.org.ua',
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': account_activation_token.make_token(user),
                    })
                    send_mail('SFKNAU.ORG.UA - Підтвердження аккаунту', message, settings.EMAIL_HOST_USER, [email])
                    err = f"Щоб підтвердити аккаунт,перегляньте почту {email} та завершіть реєстрацію."
                    status = False
                    username = password = retpassword = name = family = email = ""
            else:
                if len(User.objects.all().filter(email = email)) == 1:
                    err += "Користувач з таким email вже існує"
                    status = False
                else:
                    err += "Користувач з таким логіном вже існує"
                    status = False

            data ={
                "username" : username,
                "password" : password,
                "retpassword":retpassword,
                "email":email,
                "name" : name,
                "family":family,
                "error":err,
                "csrf_token":csrf.get_token(request),
                "status": status,
                "user": request.user,
            }
            return getPage(request,"registr.html",data)
        else:
            data = {
                "csrf_token":csrf.get_token(request),
                "error":err,
                "status": True,
                "user": request.user,
            }
            return getPage(request,"registr.html",data)
    except Exception as ex:
        logger.exception("Помилка при реєстрації користувача")
        print(ex)
        data = {
            "username": "",
            "password": "",
            "retpassword": "",
            "email": "",
            "name": "",
            "family": "",
            "error": "Сталася непередбачена помилка при реєстрації. Спробуйте пізніше.",
            "csrf_token": csrf.get_token(request),
            "status": False,
            "user": request.user,
        }
        return getPage(request, "registr.html", data)




def activate(request, uidb64, token):
    try:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return getPage(request,"void.html",{"context":'<h1 style="color:lightgreen;">Успішна реєстрація</h1>',})
        else:
            return getPage(request,"void.html",{"context":'<h1 style="color:red;">Токен не співпадає</h1><a href="/registration">Спробуйте ще раз пройти реєстрацію<a>',})
    except Exception as ex:
        print(ex)


def reset_password(request):
    if request.method == "GET":
        data = {
            "csrf_token": csrf.get_token(request),
            "user": request.user,
            "succes": True,
        }
        return getPage(request, "reset_psw.html", data)

    elif request.method == "POST":
        email = request.POST.get("email", "").strip()
        data = {
            "csrf_token": csrf.get_token(request),
            "user": request.user,
        }

        try:
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                message = loader.render_to_string('email_reset.html', {
                    'user': user,
                    'domain': 'sfknau.org.ua',
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })
                send_mail(
                    'SFKNAU.ORG.UA - Відновлення доступу',
                    message,
                    settings.EMAIL_HOST_USER,
                    [email]
                )
                data.update({
                    "status": True,
                    "error": f"Перевірте пошту {email} та перейдіть за посиланням!"
                })
            else:
                data.update({
                    "status": False,
                    "error": f"На пошту {email} немає зареєстрованих користувачів! Перевірте правильність введених даних"
                })

        except Exception as ex:
            print(ex)
            data.update({
                "status": False,
                "error": "Невідома помилка при відновленні паролю."
            })

        return getPage(request, "reset_psw.html", data)

    else:
        data = {
            "csrf_token": csrf.get_token(request),
            "user": request.user,
            "status": False,
            "error": "Невідома помилка"
        }
        return getPage(request, "reset_psw.html", data)


def reset_psw_link(request, uidb64=None, token=None):
    if request.method == "GET":
        if uidb64 == None or token == None:
            return redirect("/reset_password")
        try:
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = User.objects.get(pk=uid)
            except(TypeError, ValueError, OverflowError, User.DoesNotExist):
                user = None
            if user is not None and account_activation_token.check_token(user, token):
                data = {
                    "csrf_token":csrf.get_token(request),
                    "user": request.user,
                    "pk" : uid,
                    "login" : user.username,
                    "reset": True,
                    "status": True,
                }
                return getPage(request,"reset_psw.html",data)
            else:
                data = {
                    "csrf_token":csrf.get_token(request),
                    "user": request.user,
                    "status": False,
                    "error" : "Невідома помилка, спробуйте ще раз"
                }
                return getPage(request,"reset_psw.html",data)
        except Exception as ex:
            print(ex)
    elif request.method == "POST":
        try:
            try:
                user = User.objects.get(pk=request.POST["uidb64"])

            except(TypeError, ValueError, OverflowError, User.DoesNotExist) as ex:
                print(ex)
                data ={
                    "context" : "<p> Пароль не було змінено</p><p>Спробуйте ще раз або зверніться до адміністратора</p>",
                }
                return getPage(request,"void.html",data)
            password = request.POST["password"]
            user.set_password(password)
            user.save()
            login(request,user)
            data ={
                "context" : "<p style =  'font-size:1.3em;color:green;' > Пароль було змінено</p><p style =  'font-size:1.1em;color:steelblue;'> <a href='/'> Повернутись на головну</a> </p>",
            }
            return getPage(request,"void.html",data)
        except Exception as ex:
            print(ex)




def timetable(request):
    try:
        data = Timetable.objects.all().values()
        json_data = {'data':[data]}
        print(json_data)
        return JsonResponse({"data": list(data)})
    except Exception as ex:
        print(repr(ex))

