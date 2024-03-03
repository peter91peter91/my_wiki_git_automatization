import shutil, gitlab, os, urllib.parse, difflib, time, re
import sys

from git import Repo

access_token = os.environ.get('WIKI_ACCESS_TOKEN')  # !!!token moiseev petr gitlab компания(added in CICD of Project 935)
gitlab_url = os.environ.get('GITLAB_URL')
username = os.environ.get('WIKI_USERNAME')
project_id = os.environ.get('WIKI_PROJECT_ID')
path_to_project = os.environ.get('PROJECT_PATH')

repository_path_with_login = f"https://{username}:{access_token}@{path_to_project}"
wiki_path_with_login = repository_path_with_login.replace('.git', '.wiki.git')

project_clone_path = "/tmp/project"
wiki_clone_path = "/tmp/projects_wiki"
base_path_in_project = os.path.join(project_clone_path, "BASE")
base_path_in_wiki_clone_path = os.path.join(wiki_clone_path, "BASE")

gl = gitlab.Gitlab(gitlab_url, private_token=access_token)
project = gl.projects.get(project_id)


def clone_project_and_wiki_and_clean_wiki():
    Repo.clone_from(repository_path_with_login, project_clone_path)
    repo_wiki = Repo.clone_from(wiki_path_with_login, wiki_clone_path)


def copy_files_from_project_to_wiki():
    try:
        if os.path.exists(wiki_clone_path):shutil.rmtree(wiki_clone_path)
        shutil.copytree(base_path_in_project, base_path_in_wiki_clone_path)
    except (OSError, IOError) as e:
        print(f'Failed to copy files: {e}')
        sys.exit(1)


def gitlab_wiki_content_update():
    try:
        wikis = project.wikis.list()
        wiki_slugs = [wiki.slug for wiki in wikis]
        local_wiki_slugs = set()
        print('-' * 50)
        print('!double spaces in the names of folders and files will be removed due to the specifics of the GITLAB WIKI!')
        print('-' * 50)

        print('+++List of wikis FOR debug INFO:')
        print('-' * 3)
        for wiki_slug in wiki_slugs:
            print(wiki_slug)
        print('-' * 50)
        print('-' * 50)
        print('-' * 50)

        for root, dirs, files in os.walk(base_path_in_wiki_clone_path):
            for file in files:
                print('-' * 50)
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    try:
                        content = f.read().decode()
                        page_title = os.path.relpath(file_path, base_path_in_wiki_clone_path)
                        page_title = re.sub(' +', ' ', page_title).replace(' ', '-')
                        wiki_page_slug = '/'.join(
                            [re.sub(' +', ' ', component).strip().replace(' ', '-') for component in
                             page_title.split('/')])
                        wiki_page_data = {"title": page_title, "content": content, "format": "markdown"}

                        local_wiki_slugs.add(wiki_page_slug)

                        if wiki_page_slug in wiki_slugs:
                            wiki_page = project.wikis.get(wiki_page_slug)
                            new_content = wiki_page_data["content"].strip()
                            old_content = wiki_page.content.strip()
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
                            print('-' * 50)
                            print(f'...preparing to create wiki page. page_title: {page_title}')
                            try:
                                wiki_page = project.wikis.create(wiki_page_data)
                                wiki_page.save()
                                print(f'+++Wiki page created. page_title={page_title}')

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
        gl.session.close()



def create_wiki_toc():
    toc = '# Оглавление\n\n'
    previous_folder = None
    file_links = ''
    root_files = []
    for root, dirs, files in sorted(os.walk(base_path_in_wiki_clone_path)):
        #markdown_files = [file for file in files if file.endswith('.md')]
        all_files = [file for file in files]

        for file in sorted(all_files):
            file_path = os.path.join(root, file)
            rel_path = " ".join(os.path.relpath(file_path, base_path_in_wiki_clone_path).split())

            sections_level = rel_path.count(os.sep)
            link = urllib.parse.quote(rel_path)
            header_indent = '#' * (sections_level + 2)

            if os.sep in rel_path:
                folder, file_name = rel_path.rsplit(os.sep, 1)
            else:
                folder = ''
                file_name = rel_path

            if folder == '':
                root_files.append(file_name)

            else:
                if previous_folder != folder:
                    if previous_folder is not None:
                        toc += f'{header_indent} {previous_folder}\n{file_links}\n---\n'
                    previous_folder = folder
                    file_links = ''

            #file_links += f'{header_indent}# [{folder} > {file_name}](./{link})\n'  # выводить путь в каждой строке
            file_links += f'{header_indent}# [{file_name.rsplit(os.sep, 1)[-1]}](./{link})\n'


    toc += f'{header_indent} {previous_folder}\n{file_links}'

    if root_files:
        toc += '---\n' * 3
        toc += '# файлы в корне wiki\n'
        for file_name in sorted(root_files):
            link = urllib.parse.quote(file_name)
            toc += f'## [{file_name.rsplit(os.sep, 1)[-1]}]({link})\n'
        toc += '---\n' * 3

    home_wiki_page = None
    print('-' * 50)
    try:
        home_wiki_page = project.wikis.get("home")
        home_wiki_page.content = toc
        home_wiki_page.save()
        print('+++Home page updated successfully')
    except gitlab.exceptions.GitlabGetError:
        try:
            home_wiki_page = {'title': "home", 'content': toc, 'format': "markdown"}
            project.wikis.create(home_wiki_page)
            print('+++Home page created successfully')
        except gitlab.exceptions.GitlabCreateError as e:
            print(f"!!!Failed to create wiki page: {e}")
            sys.exit(1)

try:
    clone_project_and_wiki_and_clean_wiki()
    copy_files_from_project_to_wiki()
    gitlab_wiki_content_update()
    create_wiki_toc()


except Exception as e:
    print(f'An unexpected error occurred: {e}')
    sys.exit(1)