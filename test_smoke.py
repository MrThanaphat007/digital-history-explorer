from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=120).run()
assert not at.exception, at.exception
for page in ["Interactive Map", "Timeline", "Data Analysis", "Archive"]:
    at.session_state["nav"] = page
    at.run()
    assert not at.exception, (page, at.exception)
    print("OK", page)
at.sidebar.toggle[0].set_value(True).run()
assert not at.exception, at.exception
print("dark OK")
