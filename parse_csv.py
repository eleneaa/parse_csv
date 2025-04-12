import pandas as pd
import matplotlib.pyplot as plt
import requests


def clean_salaries(df):
    """Обработка зарплат:
    - Если есть только salary_from или salary_to - используем его как среднее
    - Пропускаем только если оба значения NaN
    """
    # Создаем копию, чтобы избежать SettingWithCopyWarning
    df = df.copy()

    # Заполняем пропущенные значения
    df['salary_from'] = df['salary_from'].fillna(df['salary_to'])
    df['salary_to'] = df['salary_to'].fillna(df['salary_from'])

    # Удаляем строки, где оба значения NaN
    df = df.dropna(subset=['salary_from', 'salary_to'], how='all')

    return df


def get_currency_rates():
    """Получает актуальные курсы валют от ЦБ РФ"""
    try:
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js')
        data = response.json()
        rates = {
            'RUR': 1,
            'USD': data['Valute']['USD']['Value'],
            'EUR': data['Valute']['EUR']['Value'],
            'KZT': data['Valute']['KZT']['Value'] / 100  # Тенге за 100 единиц
        }

        return rates
    except Exception as e:
        print(f"Ошибка при получении курсов валют: {e}")
        # Возвращаем курсы по умолчанию, если API недоступно
        return {
            'RUR': 1,
            'USD': 90,
            'EUR': 100,
            'KZT': 0.18
        }


def calculate_salary(row, currency_rates):
    """Расчет зарплаты с учетом валюты"""
    if pd.isna(row['salary_from']) and pd.isna(row['salary_to']):
        return None
    salary = (row['salary_from'] + row['salary_to']) / 2
    return salary * currency_rates.get(row['salary_currency'], 1)


def plot_top_cities_by_year(df, top_n=10):
    """Топ городов по количеству вакансий для каждого года"""
    years = sorted(df['year'].unique())

    for year in years:
        year_data = df[df['year'] == year]
        if len(year_data) == 0:
            continue

        cities = year_data['area_name'].value_counts().head(top_n)

        if len(cities) == 0:
            continue

        plt.figure(figsize=(12, 6))
        cities.plot(kind='bar', color='lightblue')
        plt.title(f'Топ-{top_n} городов по вакансиям в {year} году', pad=20)
        plt.xlabel('Город')
        plt.ylabel('Количество вакансий')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()


def plot_salaries(df):
    """График зарплат по годам"""
    plt.figure(figsize=(12, 6))

    # Средняя зарплата по годам
    salary_by_year = df.groupby('year')['salary'].mean()
    salary_by_year.plot(kind='line', marker='o', label='Средняя зарплата')

    # Медианная зарплата по годам
    median_by_year = df.groupby('year')['salary'].median()
    median_by_year.plot(kind='line', marker='o', label='Медианная зарплата')

    plt.title('Динамика зарплат по годам', pad=20)
    plt.xlabel('Год')
    plt.ylabel('Зарплата (руб)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_skills(df, top_n=15):
    """График ключевых навыков"""
    # Разбиваем навыки и считаем частоту
    skills = (
        df['key_skills']
        .str.lower()
        .str.split(r',\s*|\s*и\s*|\s*/\s*', regex=True)  # Разделители: запятые, "и", слэши
        .explode()
        .str.strip()
        .value_counts()
        .head(top_n)
    )

    plt.figure(figsize=(12, 8))
    skills.plot(kind='barh')
    plt.title(f'Топ-{top_n} ключевых навыков', pad=20)
    plt.xlabel('Количество упоминаний')
    plt.gca().invert_yaxis()  # Чтобы навыки шли сверху вниз
    plt.tight_layout()
    plt.show()


def analyze_vacancies(filename, keywords):
    """Основная функция анализа"""
    try:
        df = pd.read_csv(filename, parse_dates=['published_at'])
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        return

    # Очистка и обработка данных
    df = clean_salaries(df)
    df = df.dropna(subset=['area_name', 'name'])  # Обязательные поля

    # Фильтрация по профессии
    pattern = '|'.join(keywords)
    filtered = df[df['name'].str.contains(pattern, case=False, regex=True, na=False)]

    if len(filtered) == 0:
        print("Нет вакансий, соответствующих критериям")
        return

    # Добавляем расчетные поля
    filtered['year'] = filtered['published_at'].dt.year
    filtered['salary'] = filtered.apply(
        lambda row: calculate_salary(row, get_currency_rates()),
        axis=1
    ).dropna()

    # Анализ
    print(f"Найдено {len(filtered)} вакансий за период {filtered['year'].min()}-{filtered['year'].max()}")
    print(f"Средняя зарплата: {filtered['salary'].mean():.2f} руб")
    print(f"Медианная зарплата: {filtered['salary'].median():.2f} руб")

    # Визуализация
    plot_top_cities_by_year(filtered)
    plot_salaries(filtered)
    plot_skills(filtered)


if __name__ == "__main__":
    keywords = ["Продавец", "учитель"]
    analyze_vacancies('vacancies_2024.csv', keywords)
