run-drf:
	python3 manage.py runserver

run-fast:
	uvicorn services.fastapi.main:app --reload

mig:
	python3 manage.py makemigrations
	python3 manage.py migrate