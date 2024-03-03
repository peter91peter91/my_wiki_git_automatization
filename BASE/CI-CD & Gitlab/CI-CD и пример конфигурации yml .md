CI/CD - это сокращение от Continuous Integration (непрерывная интеграция) и Continuous Delivery (непрерывное развертывание). Это практика в сфере разработки программного обеспечения, которая объединяет автоматизированные процессы для обеспечения более быстрой, более надежной и более эффективной поставки программных продуктов.

Continuous Integration (CI) - это процесс интеграции кода разработчиков в общий репозиторий и автоматической проверки на наличие ошибок при каждом коммите. Это позволяет выявлять и устранять проблемы на ранних этапах разработки.

Continuous Delivery (CD) - это процесс автоматической сборки, тестирования и развертывания приложения в среду производства после успешной интеграции. Это обеспечивает готовность поставки приложения в любой момент, с минимальными рисками.

Файл .gitlab-ci.yml используется для определения и настройки CI/CD пайплайнов в системе управления версиями и непрерывной интеграции GitLab. Этот файл содержит описания шагов, задач и настроек, которые определяют, как процессы автоматической интеграции и развертывания будут выполняться в вашем проекте.

Вот пример файла .gitlab-ci.yml для инструмента "Temporal" с комментариями. (Его докерфайл рассмотрен в главе про докер) https://git.компания.ru/rpn/dms/devops/docker-images/temporal/-/blob/main/.gitlab-ci.yml


```
# Конфигурация CI/CD пайплайна для сборки Docker-образа

# Указываем версию Docker для совместимости
image: docker:18.09.5-git

# Определение этапов пайплайна
stages:
  - build

# Определение переменных окружения
variables:
  # Используем стратегию fetch при клонировании репозитория(загрузка исключительно изменений,а не репозитория целиком)
  GIT_STRATEGY: fetch
  # Путь к проекту в рамках CI/CD
  SHARED_PATH: $CI_PROJECT_DIR
  # Используем overlay2 как драйвер Docker
  DOCKER_DRIVER: overlay2
  # Очищаем DOCKER_TLS_CERTDIR
  DOCKER_TLS_CERTDIR: ""
  # Адрес GitLab-сервера
  GITLAB_DOMAIN: git.компания.ru
  # Идентификатор группы проекта в GitLab( в дальнейшем может быть использован в скриптах CI/CD для выполнения различных действий, специфичных для этой группы.)
  GITLAB_PROJECT_GROUP_ID: 1161
  # Токен Composer (замените на реальный токен)
  COMPOSER_TOKEN: xxxxxxxxxxxxxxx
  # Адрес реестра Docker для CI/CD
  CI_REGISTRY: registry.rpn.компания.ru
  # Имя пользователя для доступа к реестру Docker
  CI_REGISTRY_USER: cadastre
  # Пароль для доступа к реестру Docker (замените на реальный пароль)
  CI_REGISTRY_PASSWORD: xxxxxxxxxxxxxxx
  # Директория для кеширования Composer
  COMPOSER_CACHE_DIR: "$CI_PROJECT_DIR/.composer_cache"

# Определение настроек кеширования
cache:
  key: "$CI_COMMIT_REF_SLUG"
  paths:
    - .composer_cache/

# Определение задачи для сборки Docker-образа
Сборка образа:
  image: docker:git
  stage: build
  before_script:
    # Вход в реестр Docker
    - docker login -u "$CI_REGISTRY_USER" -p "$CI_REGISTRY_PASSWORD" $CI_REGISTRY
  variables:
    # Название задачи
    JOB_NAME: "build-docker-image"
    # Имя образа в реестре Docker
    CI_REGISTRY_IMAGE: registry.rpn.компания.ru/${CI_PROJECT_PATH}
  tags:
    - docker
    - builds
  script:
    # Определение тега для Docker-образа
    - |
      if [[ $CI_COMMIT_TAG != "" ]]; then
        tag=":$CI_COMMIT_TAG"
        echo "Running on branch '$CI_COMMIT_BRANCH': TAG = $TAG"
      elif [[ "$CI_COMMIT_BRANCH" == "$CI_DEFAULT_BRANCH" ]]; then
        tag=""
        echo "Running on default branch '$CI_DEFAULT_BRANCH': TAG = ':latest'"
      else
        tag=":$CI_COMMIT_REF_SLUG"
        echo "Running on branch '$CI_COMMIT_BRANCH': TAG = $TAG"
      fi
    # Запись информации о сборке в файл
    - echo "$(git log --pretty=format:'%h' -n 1) $(date +%m%d%H%M)" > build-date.txt
    # Установка утилиты jq
    - apk add jq
    # Сборка Docker-образа
    - docker build --pull -t "${DOCKER_ENV_CI_REGISTRY_IMAGE:-$CI_REGISTRY_IMAGE}${tag}" .
    # Публикация Docker-образа в реестре Docker
    - docker push "${DOCKER_ENV_CI_REGISTRY_IMAGE:-$CI_REGISTRY_IMAGE}${tag}"
```