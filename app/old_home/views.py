
from . import home


@home.route('/home/projects/', methods=['GET'])
def home_page():
	"""
	Home page

	Returns list of projects with:
	- visibility level
	- roles (of the current user if logged in)
	"""
	# projects_info = project_service.get_hub_summary()
	# js = json.dumps(projects_info)
	# resp = Response(js, status=200,  mimetype='application/json')
	
	return {}