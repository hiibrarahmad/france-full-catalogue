# Études en France – full course catalogue

A fast, searchable copy of **every course** in the official
[Études en France catalogue](https://etudesenfrance.diplomatie.gouv.fr/catalogue-formations) (17,000+ listings):
licences, bachelors, BUT, masters, engineering diplomas, Mastère Spécialisé, PhD, French-language courses and more.

**Live site:** https://hiibrarahmad.github.io/france-full-catalogue/

For a shortlist of the programs a 4-year bachelor's holder with embedded / biomedical experience can apply to,
see the companion dashboard: https://hiibrarahmad.github.io/france-masters-dashboard/

## Features

- Search by title, school, city or subject.
- Filter by open/closed status, the level you'd join (Bac+1 … Bac+8), teaching language, degree type, catalogue fee,
  city, contact email and separate-school-application requirement.
- **English proof**: each listing's text is scanned for IELTS / TOEFL / PTE / TOEIC / Cambridge / Duolingo and for
  wording that accepts a Medium of Instruction (MOI) certificate. "Not stated" means the listing doesn't say – ask the school.
- Contact email, entry years, fees and a link back to the official listing for every course.
- Copy results or emails as CSV for Excel / Google Sheets.

## Refresh the data

```bash
python scripts/fetch_catalogue.py   # downloads list + every course's details (slow; resumes if interrupted)
python scripts/build.py             # writes data/catalogue.js
```

> Fees shown are what each school entered in the catalogue. Public universities charge non-EU students
> €3,950/yr for a master (2026-27) even when a lower amount is shown. Always confirm on the school's website.
