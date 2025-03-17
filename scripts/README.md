# AquaMind Infrastructure Test Data

This directory contains scripts for initializing and managing test data for the AquaMind system.

## Test Data Initialization Script

The `init_test_data.py` script creates a complete set of infrastructure test data for the AquaMind system. This includes:

- Geographies (Faroe Islands, Scotland)
- Areas (A57 - Fuglafjørður)
- Freshwater Stations (S24 - Á Strond)
- Container Types (Egg&Alevin Trays, Fry Rearing Tanks, Parr Rearing Tanks, Smolt Tanks, Post-Smolt Tanks, Sea Pens)
- Halls (A through K)
- Containers (multiple containers of each type in appropriate halls and areas)
- Species (Atlantic Salmon)
- Life Cycle Stages (Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult)

### Usage

To run the script and initialize the test data:

```bash
# From the project root directory
python manage.py shell < scripts/init_test_data.py
```

### Container Distribution

The script creates the following containers:

| Container Type | Location | Quantity | Volume (m³) |
|----------------|----------|----------|-------------|
| Egg&Alevin Trays | Hall A | 50 | 3 |
| Fry Rearing Tanks | Hall B | 12 | 15 |
| Fry Rearing Tanks | Hall C | 12 | 15 |
| Parr Rearing Tanks | Hall D | 8 | 50 |
| Parr Rearing Tanks | Hall E | 8 | 50 |
| Smolt Tanks | Hall F | 6 | 400 |
| Smolt Tanks | Hall G | 6 | 400 |
| Smolt Tanks | Hall H | 6 | 400 |
| Post-Smolt Tanks | Hall I | 6 | 1,200 |
| Post-Smolt Tanks | Hall J | 6 | 1,200 |
| Post-Smolt Tanks | Hall K | 6 | 1,200 |
| Sea Pens | Area A57 | 24 | 42,000 |

### Data Backup

A backup of all infrastructure and batch data has been saved as `test_data_backup.json` in the project root directory. You can restore this data using:

```bash
# From the project root directory
python manage.py loaddata test_data_backup.json
```

## Database Reset

If you need to completely reset the database and then initialize test data:

```bash
# Drop and recreate the database (adjust as needed for your database)
python manage.py reset_db --noinput

# Run migrations
python manage.py migrate

# Initialize test data
python manage.py shell < scripts/init_test_data.py
```
