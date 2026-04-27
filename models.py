import datetime
from mptt.models import MPTTModel, TreeForeignKey
from django.db import models

from django_ckeditor_5.fields import CKEditor5Field

from unittest.util import _MAX_LENGTH
from django.utils import timezone
from django.utils.timezone import now
from django.contrib.auth.models import User,Group

from .timeutils import to_kyiv
#from redactor.fields import RedactorField


class Navigation(MPTTModel):
    linktext = models.CharField('Текст посилання', max_length=50)
    linktype = models.IntegerField('Тип (0 = Статичне, 1 = Динамічне)')
    link = models.CharField('URL', max_length=200)
    parent = TreeForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Батько'
    )
    is_visible = models.IntegerField('Відображати (0 = Ні, 1 = Так)', default=1)
    ico_nav = models.CharField(
        'Іконка',
        max_length=250,
        default="",
        blank=True,
        help_text='Назва іконки FA (наприклад: house) або шлях до файлу'
    )
    is_header = models.BooleanField('Заголовок категорії', default=False)

    def __str__(self):
        return f"{self.linktext} ← {self.parent.linktext}" if self.parent else self.linktext

    class MPTTMeta:
        order_insertion_by = ['linktext']

    class Meta:
        verbose_name = 'Пункт навігації'
        verbose_name_plural = 'Пункти навігації'





class Biblio(models.Model):
    code = models.CharField('Код спеціальності', max_length=10, default='', blank=True)
    name = models.CharField('Назва спеціальності', max_length=200, default='', blank=True)
    Speciality = models.CharField('Спеціальність (застаріле поле)', max_length=250, default='', blank=True)
    created_at = models.DateTimeField('Створено', default=now, editable=False)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    @property
    def created_local(self):
        return to_kyiv(self.created_at)

    @property
    def updated_local(self):
        return to_kyiv(self.updated_at)


    def save(self, *args, **kwargs):
        if self.code and self.name:
            self.Speciality = f"{self.code} | {self.name}"
        elif self.name:
            self.Speciality = self.name
        super().save(*args, **kwargs)

    def __str__(self):
        if self.code and self.name:
            return f"{self.code} | {self.name}"
        elif self.name:
            return self.name
        elif self.code:
            return self.code
        elif self.Speciality:
            return self.Speciality
        return "(Без назви)"

    class Meta:
        verbose_name = 'Спеціальності бібліотеки коледжу'
        verbose_name_plural = 'Бібліотека - Спеціальності'

class Groups(models.Model):
    groups = models.CharField('Курс', max_length=100, default='')
    created_at = models.DateTimeField('Створено', default=now, editable=False)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    @property
    def created_local(self):
        return to_kyiv(self.created_at)

    @property
    def updated_local(self):
        return to_kyiv(self.updated_at)



    def __str__(self):
        return self.groups

    class Meta:
        verbose_name = 'Курси бібліотеки коледжу'
        verbose_name_plural = 'Бібліотека - Курси'


class Biblio_MaterialCategory(models.Model):
    name = models.CharField('Назва категорії', max_length=150, unique=True)
    created_at = models.DateTimeField('Створено', default=now, editable=False)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    @property
    def created_local(self):
        return to_kyiv(self.created_at)

    @property
    def updated_local(self):
        return to_kyiv(self.updated_at)



    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Бібліотека - Категорія матеріалу'
        verbose_name_plural = 'Бібліотека - Категорії матеріалів'


class Biblio_file(models.Model):
    biblio = models.ManyToManyField('Biblio', verbose_name="Спеціальність")
    groups = models.ManyToManyField('Groups', verbose_name="Курс")
    theme = models.CharField('Тема', max_length=255, default="")
    category = models.ForeignKey(
        'Biblio_MaterialCategory',
        verbose_name="Категорія матеріалу",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    Text = models.TextField('Примітка', default="")
    link = models.CharField(
        'Посилання на drive.google.com або оберіть файл нижче.',
        max_length=255,
        default=""
    )
    File = models.FileField(
        upload_to='library/',
        default='#',
        verbose_name="Файл (не більше ніж 49,9Мб)"
    )
    member = models.CharField(max_length=255, editable=False, default='None')
    created_at = models.DateTimeField('Створено', default=now, editable=False)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    @property
    def created_local(self):
        return to_kyiv(self.created_at)

    @property
    def updated_local(self):
        return to_kyiv(self.updated_at)



    def __str__(self):
        biblio = ", ".join(str(b) for b in self.biblio.all())
        groups = ", ".join(str(g) for g in self.groups.all())
        return f"Спеціальність: {biblio}; Група: {groups}; Тема: {self.theme}"

    class Meta:
        verbose_name = 'Бібліотека - Теми'
        verbose_name_plural = 'Бібліотека - Теми'


from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=Biblio_file)
def mymodel_delete(sender, instance, **kwargs):
    try:
        instance.File.delete(False)
    except Exception as ex:
        print(ex)

class ArticlePhoto(models.Model):
    article = models.ForeignKey("Article", on_delete=models.CASCADE)
    photo = models.ForeignKey("Photo", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Фото до статті"
        verbose_name_plural = "Фото до статті"
        ordering = ['order']

    def __str__(self):
        return f"{self.article.title} → {self.photo.title or self.photo.photo.name}"

class Article(models.Model):
    title = models.CharField('Название статьи', max_length = 200)
    title_logo_link = models.CharField('Ссылка на картинку', max_length=200, default="#", blank=True, null=True)
    photos = models.ManyToManyField("Photo", through="ArticlePhoto", blank=True)
    is_pinned = models.BooleanField(default=False, verbose_name="Закріпити новину")
    detail_linktype = models.IntegerField('Тип ссылки detail (static=0,dynamic=1)',default=0)
    detail_link = models.CharField('Ссылка на детальную информацию', max_length = 200,default="#")
    detail_target = models.IntegerField('Цель ссылки detail (в этом месте=0,в новой вкладке=1)',default=0)
    return_linktype = models.IntegerField('Тип ссылки return (static=0,dynamic=1)',default=0)
    return_link = models.CharField('Ссылка возврата', max_length = 200,default='get__articles')
    article_description = models.TextField('Краткое описание',default="#")
    article_text = CKEditor5Field('Текст статті', config_name='default')
    text_as_html = models.IntegerField('Признак текста как HTML (text=0,html=1)',default=0)
    pub_date = models.DateTimeField('дата публикации')
    
    def __str__(self):
        return self.title
    
    def was_published_recently(self):
        return self.pub_date >= (timezone.now() - datetime.timedelta(days = 7))
    
    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-pub_date']


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete = models.CASCADE)
    author_name = models.CharField('author of comment', max_length = 50)
    comment_text = models.CharField('comment text', max_length = 200)
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return f'Автор: {self.author_name}; Коментар: {self.comment_text}'

class Vip(models.Model):
    vipname = models.CharField('Имя пользователя', max_length = 50,default="#")
    password = models.CharField('пароль', max_length = 20,default="#")

    class Meta:
        verbose_name = 'VIP пользователь'
        verbose_name_plural = 'VIP пользователи'

    def __str__(self):
        return self.vipname

class Timetable(models.Model):
    id = models.AutoField(primary_key=True)
    dt = models.DateTimeField('дата')
    tid = models.IntegerField('id преподавателя',default=0)
    fam = models.CharField('Фамилия преподавателя', max_length = 30,default="#")
    pair = models.IntegerField('номер пары',default=0)
    gid = models.IntegerField('id группы',default=0)
    gname = models.CharField('Наименование группы', max_length = 255,default="#")
    kod = models.IntegerField('код',default=0)
    lesson = models.CharField('Наименование дисциплины', max_length = 30,default="#")

    def __str__(self):
        return str(self.dt) + ", " + str(self.pair) + ", " + self.fam + ", " + self.gname + ", " + self.lesson 

    class Meta:
        verbose_name = 'Расписание'
        verbose_name_plural = 'Расписание'

class VideoFile(models.Model):
    file_obj = models.FileField(upload_to='media/')
    description = models.CharField('Описание видео', max_length = 300,default="#")

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Видеофайл'
        verbose_name_plural = 'Видеофайлы'



class Album(models.Model):
    id = models.AutoField(primary_key=True)
    pic = models.ImageField('Іконка', upload_to="images/", null=True)
    folder = models.CharField('Ім’я каталогу', max_length=60, default='folder')
    title = models.CharField('Опис альбому', max_length=60, blank=True, null=True)
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    def __str__(self):
        return self.title or "Без назви"


    def save(self, *args, **kwargs):
        if self.order == 0:
            max_order = Album.objects.aggregate(models.Max('order'))['order__max'] or 0
            self.order = max_order + 1
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Альбом'
        verbose_name_plural = 'Альбоми'
        ordering = ['order']


class Tag(models.Model):
    tag = models.CharField('Тег', max_length=50)

    def __str__(self):
        return self.tag

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'


class Photo(models.Model):
    title = models.CharField('Опис', max_length=60, blank=True, null=True)
    photo = models.FileField(upload_to="images/")
    tags = models.ManyToManyField(Tag, blank=True)
    albums = models.ManyToManyField(Album, blank=True, through='PhotoAlbum')
    created = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=50)
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    def __str__(self):
        return self.photo.name

    def save(self, *args, **kwargs):
        if self.order == 0:
            max_order = Photo.objects.aggregate(models.Max('order'))['order__max'] or 0
            self.order = max_order + 1
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Фото'
        verbose_name_plural = 'Фотографії'
        ordering = ['order']

class PhotoAlbum(models.Model):
    photo = models.ForeignKey("Photo", on_delete=models.CASCADE, verbose_name="Фотографія")
    album = models.ForeignKey("Album", on_delete=models.CASCADE, verbose_name="Альбом")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        ordering = ['order']
        verbose_name = "Зв'язок Фото-Альбом"
        verbose_name_plural = "Зв'язки Фото-Альбом"


class Notify(models.Model):
    users = models.ManyToManyField(User,verbose_name="Користувачі",blank=True,related_name='ForUsers')
    groups = models.ManyToManyField(Group,verbose_name="Групи користувачів",blank=True)
    head_notify = models.CharField('Заголовок',max_length=255,default='')
    text_notify = models.TextField('Повідомлення',default="")
    users_read = models.ManyToManyField(User,verbose_name="Прочитавщі користувачі",blank=True,related_name='ReadsUsers')
    def __str__(self):
        return self.text_notify

    class Meta:
        verbose_name = 'Повідомлення'
        verbose_name_plural = 'Повідомлення'

    def clean(self):
        print(self.__dict__)
        
