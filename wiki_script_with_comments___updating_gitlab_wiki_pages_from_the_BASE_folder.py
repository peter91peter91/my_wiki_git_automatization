import shutil, gitlab, os, urllib.parse, difflib, time, re
import sys

from git import Repo

# Извлекаем данные аутентификации и информацию о проекте из переменных окружения
access_token = os.environ.get('WIKI_ACCESS_TOKEN')
gitlab_url = os.environ.get('GITLAB_URL')
username = os.environ.get('WIKI_USERNAME')
project_id = os.environ.get('WIKI_PROJECT_ID')
path_to_project = os.environ.get('PROJECT_PATH')

# Формируем пути на основе полученных переменных
repository_path_with_login = f"https://{username}:{access_token}@{path_to_project}"
wiki_path_with_login = repository_path_with_login.replace('.git', '.wiki.git')

# Задаем временные пути к клонам проекта и его вики
project_clone_path = "/tmp/project"
wiki_clone_path = "/tmp/projects_wiki"

# Пути к основе проекта и его вики
base_path_in_project = os.path.join(project_clone_path, "BASE")
base_path_in_wiki_clone_path = os.path.join(wiki_clone_path, "BASE")

# Инициализируем соединение с GitLab
gl = gitlab.Gitlab(gitlab_url, private_token=access_token)
# Получаем проект
project = gl.projects.get(project_id)


def clone_project_and_wiki_and_clean_wiki():
    # Клонируем проект и его вики
    Repo.clone_from(repository_path_with_login, project_clone_path)
    repo_wiki = Repo.clone_from(wiki_path_with_login, wiki_clone_path)


def copy_files_from_project_to_wiki():
    try:
        # Если вики уже существует, удаляем её
        if os.path.exists(wiki_clone_path): shutil.rmtree(wiki_clone_path)
        # Копируем файлы из проекта в вики
        shutil.copytree(base_path_in_project, base_path_in_wiki_clone_path)
    except (OSError, IOError) as e:
        # Обработка исключений, связанных с ошибками операционной системы и ввода-вывода
        print(f'Failed to copy files: {e}')
        sys.exit(1)  # Если ошибка возникла, останавливаем выполнение скрипта








##########################
##########################
##########################
##########################
# "Если текущая папка отличается от предыдущей": происходит ли изменение в текущей обрабатываемой папке?
# Если folder и previous_folder не равны, это значит, что мы перешли к новой папке.
# "Если есть предыдущая папка, добавляем ее в оглавление": Это условие проверяет,
# что previous_folder не равно None, то есть это не первая папка, которую мы обрабатываем.
# Если это так, то предыдущая папка и информация о ее файлах (file_links) добавляются в toc
# (оглавление). Затем добавляется разделитель (---\n).
# "Обновляем текущую папку": Значение previous_folder обновляется текущим значением folder,
# то есть текущая папка становится "предыдущей" для следующего цикла обработки.







def gitlab_wiki_content_update():
    try:
        # Получаем список всех вики в проекте
        wikis = project.wikis.list()
        # Извлекаем слаги (slug) всех вики для последующего сравнения
        wiki_slugs = [wiki.slug for wiki in wikis]
        local_wiki_slugs = set()
        print('-' * 50)
        print('!double spaces in the names of folders and files will be removed due to the specifics of the GITLAB WIKI!')
        print('-' * 50)

        print('+++List of wikis FOR debug INFO:')
        print('-' * 3)
        # Выводим список слагов вики для отладки
        for wiki_slug in wiki_slugs:
            print(wiki_slug)
        print('-' * 50)
        print('-' * 50)
        print('-' * 50)

        # Проходим по всем файлам в каталоге вики
        for root, dirs, files in os.walk(base_path_in_wiki_clone_path):
            for file in files:
                print('-' * 50)
                file_path = os.path.join(root, file)
                # Открываем каждый файл
                with open(file_path, 'rb') as f:
                    try:
                        # Считываем содержимое файла
                        content = f.read().decode()
                        # Название страницы будет равно относительному пути до файла
                        page_title = os.path.relpath(file_path, base_path_in_wiki_clone_path)
                        # Чистим название страницы от лишних пробелов и форматируем слаг страницы
                        page_title = re.sub(' +', ' ', page_title).replace(' ', '-')
                        wiki_page_slug = '/'.join(
                            [re.sub(' +', ' ', component).strip().replace(' ', '-') for component in
                             page_title.split('/')])
                        # Формируем данные для вики-страницы
                        wiki_page_data = {"title": page_title, "content": content, "format": "markdown"}

                        # Добавляем слаг нашей локальной страницы в сет
                        local_wiki_slugs.add(wiki_page_slug)

                        # Если такая страница уже существует в вики GitLab, обновляем ее
                        if wiki_page_slug in wiki_slugs:
                            wiki_page = project.wikis.get(wiki_page_slug)
                            new_content = wiki_page_data["content"].strip()
                            old_content = wiki_page.content.strip()
                            # Если контент новой страницы отличается от старого, обновляем его
                            if new_content != old_content:
                                print(f'...preparing to update wiki page. page_title: {page_title}')
                                print('-' * 50)
                                diff = difflib.unified_diff(old_content.splitlines(), new_content.splitlines())
                                print('...Differences between the old and new content...: \n' + '\n'.join(diff))
                                wiki_page.content = new_content
                                wiki_page.title = wiki_page_slug
                                try:
                                    wiki_page.save()
                                    print(f'+++the page was updated. page_title: {page_title}')
                                except gitlab.exceptions.GitlabUpdateError as e:
                                    print(f'!!!Failed to update wiki page!!!: {e}')
                                    sys.exit(1)
                            else:
                                print(f'+++No changes in the content for page_title={page_title}. No need for update.')
                        else:
                            # Если вики-страницы не существует, создаем ее
                            print('-' * 50)
                            print(f'...preparing to create wiki page. page_title: {page_title}')
                            try:
                                wiki_page = project.wikis.create(wiki_page_data)
                                wiki_page.save()
                                print(f'+++Wiki page created. page_title={page_title}')

                                # Дополнительная проверка: убеждаемся в том, что страница действительно создана
                                wikis = project.wikis.list(all=True)
                                wiki_slugs = [wiki.slug for wiki in wikis]
                                was_created = False
                                for wiki in wikis:
                                    if wiki.slug == wiki_page_slug:
                                        was_created = True
                                        break

                                if was_created:
                                    print(
                                        f'+++Title of the created page exists in GitLab. page_title={page_title}, wiki_page_slug={wiki_page_slug}')
                                else:
                                    print(
                                        f'!!!ERROR, The created wiki page was not found in GitLab wikis. page_title={page_title}, wiki_page_slug={wiki_page_slug}')
                                    sys.exit(1)
                                print('-' * 50)
                            except gitlab.exceptions.GitlabCreateError as e:
                                print(f'!!!Failed to create wiki page: {e}')
                                sys.exit(1)
                    except UnicodeDecodeError:
                        print(f"!!!Unable to read file as text!!!: {file_path}")
                        sys.exit(1)

        # Удаляем вики-страницы, которых нет в локальной версии
        for wiki_slug in wiki_slugs:
            if wiki_slug not in local_wiki_slugs and wiki_slug != 'home':
                print('-' * 50)
                print('-' * 50)
                print('-' * 50)
                print(f'...preparing to delete wiki page. Slug: {wiki_slug}')
                try:
                    wiki_page = project.wikis.get(wiki_slug)
                    wiki_page.delete()
                    print(f'+++ Wiki page deleted. Slug: {wiki_slug}')
                except gitlab.exceptions.GitlabDeleteError as e:
                    print(f'!!!Failed to delete wiki page!!!: {e}')
                    sys.exit(1)

    except gitlab.exceptions.GitlabGetError as e:
        print(f'!!!Failed to get wiki!!!: {e}')
        sys.exit(1)
    finally:
        # Закрываем сессию
        gl.session.close()







##########################
    #ВСЕ ПУТИ В ДАННЫХ ССЫЛКАХ С ПРОЦЕНТАМИ БУДУТ РАБОТАТЬ ОТНОСИТЕЛЬНО РУТА ВИКИ. (ТОЧКИ ./  )
    # Добавляем ссылку на текущий файл в список ссылок текущей папки
    #При каждом прохождении цикла (не показан в вашем фрагменте кода), file_links будет расти,
    # добавляя каждый раз новую строку с информацией о файле.



def create_wiki_toc():
    # Создаем начало оглавления
    toc = '# Оглавление\n\n'
    # Инициализируем переменную для хранения предыдущей папки
    previous_folder = None
    # Инициализируем строку для хранения ссылок на файлы
    file_links = ''
    # Инициализируем список для хранения файлов в корневой папке
    root_files = []

    # Проходим по всем файлам в каталоге вики
    for root, dirs, files in sorted(os.walk(base_path_in_wiki_clone_path)):

        # Берем список всех файлов
        all_files = [file for file in files]

        # Обходим все файлы в текущей директории
        for file in sorted(all_files):
            # Получаем полный путь к файлу
            file_path = os.path.join(root, file)
            # Получаем относительный путь файла в формате "секция/подсекция/файл"
            rel_path = " ".join(os.path.relpath(file_path, base_path_in_wiki_clone_path).split())

            # Уровень вложенности секции определяем по количеству разделителей в пути
            sections_level = rel_path.count(os.sep)
            # Преобразуем путь в URL
            link = urllib.parse.quote(rel_path)
            # Определяем уровень заголовка в зависимости от уровня вложенности
            header_indent = '#' * (sections_level + 2)

            # Если есть разделитель пути, разделяем путь на папку и имя файла
            if os.sep in rel_path:
                folder, file_name = rel_path.rsplit(os.sep, 1)
            else:
                # Иначе создаем пустую папку и помещаем имя файла в переменную file_name
                folder = ''
                file_name = rel_path

            # Если путь к файлу не содержит папку, добавляем имя файла в список файлов корня
            if folder == '':
                root_files.append(file_name)

            else:
                # Если текущая обрабатываемая папка отличается от предыдущей
                if previous_folder != folder:
                    # Если есть предыдущая папка, добавляем к оглавлению ссылки на все файлы из предыдущей папки
                    if previous_folder is not None:
                        toc += f'{header_indent} {previous_folder}\n{file_links}\n---\n'
                    # И обновляем предыдущую папку на текущую
                    previous_folder = folder
                    # Сбрасываем список ссылок на файлы
                    file_links = ''

                # Добавляем новую ссылку на файл в список ссылок
                file_links += f'{header_indent}# [{file_name.rsplit(os.sep, 1)[-1]}](./{link})\n'

        # Добавляем оставшиеся ссылки на файлы последней папки к оглавлению
        toc += f'{header_indent} {previous_folder}\n{file_links}'

        # Если есть файлы в корне, добавляем их к оглавлению
        if root_files:
            toc += '---\n' * 3
            toc += '# файлы в корне wiki\n'
            for file_name in sorted(root_files):
                link = urllib.parse.quote(file_name)
                toc += f'## [{file_name.rsplit(os.sep, 1)[-1]}]({link})\n'
            toc += '---\n' * 3

        # Если главная страница существует, обновляем ее
        home_wiki_page = None
        print('-' * 50)
        try:
            home_wiki_page = project.wikis.get("home")
            home_wiki_page.content = toc
            home_wiki_page.save()
            print('+++Home page updated successfully')
        # Иначе создаем новую
        except gitlab.exceptions.GitlabGetError:
            try:
                home_wiki_page = {'title': "home", 'content': toc, 'format': "markdown"}
                project.wikis.create(home_wiki_page)
                print('+++Home page created successfully')
            # В случае ошибки создания страницы выводим соответствующее сообщение
            except gitlab.exceptions.GitlabCreateError as e:
                print(f"!!!Failed to create wiki page: {e}")
                sys.exit(1)



#ЗАПУСК ПРОГРАММЫ
try:
    clone_project_and_wiki_and_clean_wiki()
    copy_files_from_project_to_wiki()
    gitlab_wiki_content_update()
    create_wiki_toc()


except Exception as e:
    print(f'An unexpected error occurred: {e}')
    sys.exit(1)