from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import serve
from django.contrib.sitemaps.views import sitemap
from sc.sitemaps import NavigationSitemap, StaticPagesSitemap, DynamicPagesSitemap
from . import views
from .views import resume_view, StartPage
from . import library_views as lib
from .feeds import LatestArticlesFeed
from .feeds import latest_articles_json_feed


app_name = 'scnau'

# Sitemaps configuration
sitemaps = {
    'navigation': NavigationSitemap,
    'static_pages': StaticPagesSitemap,
    'dynamic_pages': DynamicPagesSitemap,
}

urlpatterns = [
    path('', views.StartPage, name="StartPage"),
    path('resume/', resume_view, name='resume'),

    # Serve media and static files in development only
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

    path("search-navigation/", views.search_navigation, name="search_navigation"),
    path('load-children/<int:parent_id>/', views.load_menu_children, name='load_menu_children'),

    path('rss/news/', LatestArticlesFeed(), name='rss_news'),
    path("rss/news.json", latest_articles_json_feed, name="json_news_feed"),

    path('authUser/', views.authUser, name='authUser'),
    path('login/', views.login_page, name='login_page'),
    path('registration/', views.registration, name='registration'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('activate/<str:uidb64>/<str:token>', views.activate, name='activate'),
    path('reset_psw_link/', views.reset_psw_link, name='reset_psw_link'),
    path('reset_psw_link/<str:uidb64>/<str:token>', views.reset_psw_link, name='reset_psw_link'),
    path('logout_func/', views.logout_func, name='logout_func'),
    path('news/', views.getNews, name='get_news'),
    path('news/page=<int:article_id>/', views.getNews, name='get_news'),
    path('get__articles/', views.get_Articles, name='get__articles'),
    path('0', views.getPage, name="0"),
    path('detail/<int:article_id>', views.detail, name='detail'),
    path('new_comments/<int:article_id>', views.new_comments, name='leave_comments'),
    path('makeTimetable/', views.makeTimetable, name='makeTimetable'),
    path('selectTeacher/', views.selectTeacher, name='selectTeacher'),
    path('selectTeacher/tid=<int:tid>/', views.getTeacherTimetable, name='getTeacherTimetable'),
    path('selectGroup/', views.selectGroup, name='selectGroup'),
    path('selectGroup/gid=<int:gid>/', views.getGroupTimetable, name='selectGroup'),

    path('library/', lib.library, name='library'),
    path('library/spec=<int:id_spec>/', lib.library, name='library_spec'),
    path('library/spec=<int:id_spec>/group=<int:id_group>/', lib.library, name='library_group'),
    path('library/spec=<int:id_spec>/group=<int:id_group>/theme=<str:theme>/', lib.library, name='library_theme'),

    path('library/edit/', lib.lib_edit, name='library_edit'),
    path('library/edit/id=<int:id_file>/', lib.lib_edit, name='library_edit_id'),

    path('library/edit/spec/<int:id_spec>/', lib.edit_spec, name='edit_spec'),
    path('library/edit/group/<int:id_group>/', lib.edit_group, name='edit_group'),
    path('library/edit/theme/<str:theme>/group/<int:id_group>/spec/<int:id_spec>/', lib.edit_theme, name='edit_theme'),

    path('library/new/', lib.lib_new, name='library_new'),
    path('library/new/<str:whois>/', lib.lib_new, name='library_new'),


    path('TimetableAdmin/', views.getTimetableAdmin, name='getTimetableAdmin'),
    path('simple_upload/', views.simple_upload, name='simple_upload'),
    path('get_albums2/', views.get_Albums, name='get_albums'),
    path('albums/', views.get_Albums2, name='get_albums2'),
    path('albums/page=<int:page>/', views.get_Albums2, name='get_albums2'),
    path('photos/<int:album_id>/', views.getPhotos, name='get_photos'),
    path('photos/<int:album_id>/page=<int:page>/', views.getPhotos, name='get_photos'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    path('sitemap/', views.site_map, name='sitemap'),

    path('page/<str:page>', views.getPage, name="getPage"),
    path('notify/', views.notify, name="notify"),
    path('notify/<int:id_notify>', views.notify, name="notify_id"),
    path('getTT/', views.timetable, name="getTT"),

]
