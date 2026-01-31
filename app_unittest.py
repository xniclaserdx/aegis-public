import hashlib
import os
from socket import SocketIO
import threading
import time
import unittest
from unittest.mock import MagicMock, mock_open, patch

from flask import Flask
from flask_socketio import SocketIO, SocketIOTestClient
from app_start_login_register import (
    is_valid_email,
    session_garbage_collector_thread,
    extend_session,
    log_event,
    store_session,
    get_session,
    remove_session,
    get_session_role,
    get_session_email,
    send_email,
    send_verification_code,
    send_reset_password_email,
    is_password_strong,
    create_user_dict,
    register_user,
    get_users_from_csv,
    authenticate_user
)
import pandas as pd
import torch
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import DataLoader

from app_dashboard import (DataSimulator, SimpleNN, calculate_sha256,
                           map_uuid_to_simulation, initialize_simulation,
                           get_dashboard_template, decode_categorical_columns, reorder_columns,
                           render_template_with_table, get_user_info, start_user_simulation, stop_user_simulation,
                           reset_user_data)
from app_start_login_register import (app, create_user_dict, get_session,
                                      is_password_strong, is_valid_email,
                                      remove_session, store_session, get_user_attribute,
                                      validate_email, validate_password,
                                      is_email_registered, validate_login_email,
                                      initiate_verification, generate_coupon_cookie,
                                      generate_session_token, generate_verification_code,
                                      store_verification_coupon, get_verification_coupon,
                                      is_correct_code, login_user, generate_reset_token,
                                      validate_reset_email, user_exists, process_reset_request,
                                      find_reset_token, hash_password, update_user_password,
                                      remove_reset_token, shutdown_webserver)
from backend_train import NetDataset, evaluate, train

class TestDashboardFunctionsNoRoutes(unittest.TestCase):
    def setUp(self):
        global simulations
        simulations = [] 

    @patch('threading.Thread')
    def test_initialize_simulation(self, mock_thread):
        user_uuid = 'test-uuid'
        mock_data_simulator = MagicMock()
        with patch('app_dashboard.DataSimulator', return_value=mock_data_simulator):
            result = initialize_simulation(user_uuid)

        self.assertEqual(result['data_simulator'].uuid, user_uuid)
        mock_thread.assert_called_once()
        self.assertEqual(result['thread'], mock_thread.return_value)
    

    def test_map_uuid_to_simulation(self):
        """Test the map_uuid_to_simulation function."""
        with patch('app_dashboard.simulations', [
            ("uuid-123", {"name": "Simulation A", "status": "running"}),
            ("uuid-456", {"name": "Simulation B", "status": "stopped"}),
            ("uuid-789", {"name": "Simulation C", "status": "paused"}),
        ]):
            # Test valid UUID
            result = map_uuid_to_simulation("uuid-123")
            self.assertEqual(result, {"name": "Simulation A", "status": "running"})
            # Test invalid UUID
            result = map_uuid_to_simulation("uuid-999")
            self.assertIsNone(result)
            # Test empty UUID
            result = map_uuid_to_simulation("")
            self.assertIsNone(result)
            # Test None as UUID
            result = map_uuid_to_simulation(None)
            self.assertIsNone(result)


    def test_decode_categorical_columns(self):
        import pandas as pd
        df = pd.DataFrame({'category': [0, 1, 2]})
        le_encoders = {'category': MagicMock(classes_=['a', 'b', 'c'])}

        result = decode_categorical_columns(df, le_encoders)
        self.assertListEqual(result['category'].tolist(), ['a', 'b', 'c'])

    def test_reorder_columns(self):
        import pandas as pd
        df = pd.DataFrame({'timestamp': [1, 2], 'data': [3, 4]})

        result = reorder_columns(df)
        self.assertListEqual(result.columns.tolist(), ['timestamp', 'data'])

    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    def test_calculate_sha256(self, mock_file):
        file_path = '/mock/path/file.txt'
        expected_hash = hashlib.sha256(b'test content').hexdigest()

        result = calculate_sha256(file_path)
        self.assertEqual(result, expected_hash)
        mock_file.assert_called_once_with(file_path, 'rb')

    def test_get_user_info(self):
        with patch('app_dashboard.get_session_email', return_value='test@example.com') as mock_email, \
             patch('app_dashboard.get_session_role', return_value='admin') as mock_role:
            result = get_user_info('mock-session-data')

        self.assertEqual(result, {'email': 'test@example.com', 'role': 'admin'})
        mock_email.assert_called_once_with('mock-session-data')
        mock_role.assert_called_once_with('mock-session-data')

    @patch('app_dashboard.socketio.emit')
    @patch('threading.Thread')
    def test_start_user_simulation(self, mock_thread, mock_emit):
        mock_thread_instance = mock_thread.return_value
        mock_thread_instance.is_alive.return_value = False

        simulation = {
            'status': threading.Event(),
            'data_simulator': MagicMock(),
            'thread': mock_thread_instance
        }

        start_user_simulation(simulation)

        mock_emit.assert_called_once_with('simulation_status', {'status': 'started'})
        self.assertTrue(mock_thread_instance.start.called)

    @patch('app_dashboard.socketio.emit')
    def test_stop_user_simulation(self, mock_emit):
        simulation = {
            'status': threading.Event(),
            'data_simulator': MagicMock(),
            'thread': threading.Thread()
        }
        simulation['thread'].is_alive = MagicMock(return_value=True)
        simulation['thread'].join = MagicMock()
        
        start_user_simulation(simulation)

        stop_user_simulation(simulation)

        mock_emit.assert_called_once_with('simulation_status', {'status': 'stopped'})
        self.assertTrue(simulation['status'].is_set())
        simulation['thread'].join.assert_called_once()

    def test_reset_user_data(self):
        simulation = {
            'data_simulator': MagicMock(normal_count=5, bad_count=3, last_120_rows=[1, 2, 3])
        }

        reset_user_data(simulation)

        self.assertEqual(simulation['data_simulator'].normal_count, 0)
        self.assertEqual(simulation['data_simulator'].bad_count, 0)
        self.assertListEqual(simulation['data_simulator'].last_120_rows, [])

    def test_calculate_sha256(self):
        test_content = b'Test content for SHA256'
        test_file = 'test_file.tmp'
        with open(test_file, 'wb') as f:
            f.write(test_content)
        expected_hash = hashlib.sha256(test_content).hexdigest()
        actual_hash = calculate_sha256(test_file)
        self.assertEqual(actual_hash, expected_hash)
        os.remove(test_file)

class TestLoginRegisterFunctionsNoRoutes(unittest.TestCase):
    def test_is_valid_email(self):
        self.assertTrue(is_valid_email('test@example.com'))
        self.assertFalse(is_valid_email('invalid-email'))

    @patch('app_start_login_register.session_store', new_callable=dict)
    def test_store_session(self, mock_session_store):
        store_session('session_token', 'test@example.com', 'user', time.time() + 1800)
        self.assertIn('session_token', mock_session_store)
        self.assertEqual(mock_session_store['session_token']['email'], 'test@example.com')

    @patch('app_start_login_register.session_store', new_callable=dict)
    def test_get_session(self, mock_session_store):
        mock_session_store['session_token'] = {'email': 'test@example.com'}
        session = get_session('session_token')
        self.assertEqual(session['email'], 'test@example.com')

    @patch('app_start_login_register.session_store', new_callable=dict)
    def test_remove_session(self, mock_session_store):
        mock_session_store['session_token'] = {'email': 'test@example.com'}
        remove_session('session_token')
        self.assertNotIn('session_token', mock_session_store)

    @patch('app_start_login_register.session_store', new_callable=dict)
    def test_get_session_role(self, mock_session_store):
        mock_session_store['session_token'] = {'role': 'user'}
        role = get_session_role('session_token')
        self.assertEqual(role, 'user')

    @patch('app_start_login_register.session_store', new_callable=dict)
    def test_get_session_email(self, mock_session_store):
        mock_session_store['session_token'] = {'email': 'test@example.com'}
        email = get_session_email('session_token')
        self.assertEqual(email, 'test@example.com')

    @patch('app_start_login_register.send_email')
    def test_send_verification_code(self, mock_send_email):
        send_verification_code('test@example.com', '123456')
        mock_send_email.assert_called_with('test@example.com', '2-Factor Authentication Code', unittest.mock.ANY, is_html=True)

    @patch('app_start_login_register.open', new_callable=unittest.mock.mock_open)
    def test_log_event(self, mock_open):
        log_event('Test event')
        mock_open.assert_called_with(os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt"), "a", newline="")
        mock_open().write.assert_called_with(unittest.mock.ANY)

    def test_get_user_attribute(self):
        user_data = {'email': 'test@example.com', 'role': 'user'}
        self.assertEqual(get_user_attribute(user_data, 'email'), 'test@example.com')
        self.assertIsNone(get_user_attribute(user_data, 'invalid'))

    def test_is_password_strong(self):
        self.assertTrue(is_password_strong('StrongPass1!')[0])
        self.assertFalse(is_password_strong('weak')[0])

    def test_create_user_dict(self):
        user_data = ['test@example.com', 'hashed_password', 'user', '0']
        user_dict = create_user_dict(user_data)
        self.assertEqual(user_dict['email'], 'test@example.com')

    def test_validate_email(self):
        self.assertTrue(validate_email('test@example.com'))
        self.assertFalse(validate_email('invalid-email'))

    def test_validate_password(self):
        self.assertTrue(validate_password('StrongPass1!'))
        self.assertFalse(validate_password('weak'))

    @patch('app_start_login_register.open', new_callable=unittest.mock.mock_open)
    def test_register_user(self, mock_open):
        self.assertTrue(register_user('test@example.com', 'StrongPass1!'))

    def test_validate_login_email(self):
        self.assertTrue(validate_login_email('test@example.com'))
        self.assertFalse(validate_login_email('invalid-email'))

    @patch('app_start_login_register.open', new_callable=unittest.mock.mock_open, read_data='test@example.com,hashed_password,user,0\n')
    def test_get_users_from_csv(self, mock_open):
        users = get_users_from_csv()
        self.assertEqual(users[0]['email'], 'test@example.com')

    def test_authenticate_user(self):
        users = [{'email': 'test@example.com', 'hashed_password': hashlib.sha256(('StrongPass1!' + os.getenv("PASSWORD_PEPPER") + 'test@example.com').encode()).hexdigest()}]
        user = authenticate_user(users, 'test@example.com', 'StrongPass1!')
        self.assertEqual(user['email'], 'test@example.com')

    @patch('app_start_login_register.send_verification_code')
    @patch('app_start_login_register.prepare_verification_response')
    def test_initiate_verification(self, mock_prepare_response, mock_send_verification_code):
        user = {'email': 'test@example.com', 'hashed_password': 'hashed_password'}
        form = MagicMock()
        response = MagicMock()
        mock_prepare_response.return_value = response
        result = initiate_verification(user, form)
        self.assertEqual(result, response)
        mock_send_verification_code.assert_called()

    def test_generate_coupon_cookie(self):
        response = MagicMock()
        result = generate_coupon_cookie(response)
        self.assertTrue(result.isdigit())
        response.set_cookie.assert_called_with('coupon', result, secure=True, httponly=False, samesite='Lax', expires=unittest.mock.ANY)

    def test_generate_session_token(self):
        token = generate_session_token()
        self.assertTrue(isinstance(token, str))

    def test_generate_verification_code(self):
        code = generate_verification_code()
        self.assertTrue(code.isdigit())
        @patch('app_start_login_register.coupon_store', new_callable=list)
        def test_store_verification_coupon(self, mock_coupon_store):
            user = {'email': 'test@example.com', 'hashed_password': 'hashed_password', 'role': 'user'}
            store_verification_coupon(user, 'coupon_cookie_value', 'session_token', 'verification_code')
            self.assertEqual(mock_coupon_store[0]['email'], 'test@example.com')

        @patch('app_start_login_register.coupon_store', [{'coupon_cookie': 'coupon_cookie_value', 'email': 'test@example.com'}])
        def test_get_verification_coupon(self, mock_coupon_store):
            coupon = get_verification_coupon('coupon_cookie_value')
            self.assertEqual(coupon['email'], 'test@example.com')

    def test_is_correct_code(self):
        correct_code = hashlib.sha256('123456'.encode()).hexdigest()
        self.assertTrue(is_correct_code('123456', correct_code))
        self.assertFalse(is_correct_code('654321', correct_code))

    @patch('app_start_login_register.store_session')
    def test_login_user(self, mock_store_session):
        response = MagicMock()
        verification_coupon = {'email': 'test@example.com', 'session_token': 'session_token', 'role': 'user'}
        result = login_user(response, verification_coupon)
        mock_store_session.assert_called_with('session_token', 'test@example.com', 'user', unittest.mock.ANY)
        response.set_cookie.assert_called_with('logged_in', 'session_token', secure=True, httponly=False, samesite='Lax', expires=unittest.mock.ANY)
        self.assertEqual(result, response)

    def test_generate_reset_token(self):
        token = generate_reset_token('test@example.com')
        self.assertTrue(isinstance(token['token'], str))

    def test_validate_reset_email(self):
        self.assertTrue(validate_reset_email('test@example.com'))
        self.assertFalse(validate_reset_email('invalid-email'))

    def test_user_exists(self):
        users = [{'email': 'test@example.com'}]
        self.assertTrue(user_exists(users, 'test@example.com'))
        self.assertFalse(user_exists(users, 'new@example.com'))

    @patch('app_start_login_register.send_reset_password_email')
    def test_process_reset_request(self, mock_send_reset_password_email):
        result = process_reset_request('test@example.com')
        self.assertEqual(result, "Password reset instructions have been sent to your email address.")
        mock_send_reset_password_email.assert_called()

    @patch('app_start_login_register.reset_password_tokens', new_callable=list)
    def test_find_reset_token(self, mock_reset_password_tokens):
        mock_reset_password_tokens.append({'token': 'reset_token', 'email': 'test@example.com'})
        token = find_reset_token('reset_token')
        self.assertEqual(token['email'], 'test@example.com')

    def test_hash_password(self):
        hashed_password = hash_password('StrongPass1!', 'test@example.com')
        self.assertTrue(isinstance(hashed_password, str))

    @patch('app_start_login_register.open', new_callable=unittest.mock.mock_open, read_data='test@example.com,hashed_password,user,0\n')
    def test_update_user_password(self, mock_open):
        update_user_password('test@example.com', 'new_hashed_password')
        mock_open().write.assert_called()

    @patch('app_start_login_register.reset_password_tokens', new_callable=list)
    def test_remove_reset_token(self, mock_reset_password_tokens):
        mock_reset_password_tokens.append({'token': 'reset_token', 'email': 'test@example.com'})
        remove_reset_token({'token': 'reset_token', 'email': 'test@example.com'})
        self.assertNotIn({'token': 'reset_token', 'email': 'test@example.com'}, mock_reset_password_tokens)

"""
We test only these routes as we want to check POST and GET requests, we also want to check the responses
We want to make sure that if we send a POST request, we get the correct response back
This is logic that is not tested in the functions above
"""
class TestLoginRegisterRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False

    def test_store_cookie(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['logged_in'] = 'admin_session_token'
                store_session('admin_session_token', 'admin@example.com', 'admin', time.time() + 1800)
                c.set_cookie('logged_in', 'admin_cookie')

    def test_index_redirect(self):
        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_register_get(self):
        response = self.client.get('/register', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)

    def test_register_post(self):
        response = self.client.post('/register', data={
            'email': 'test@example.com',
            'password': 'Password123!',
            'role': 'user'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)

    def test_login_get(self):
        response = self.client.get('/login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_login_post(self):
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'>AEGIS Login', response.data) 

""" 
Testing these routes is not that useful as we are not doing much in the routes 
We explain why in the documentation

Summary:
They are tested indirectly by the functions that are called by the routes
For further testing, End-to-End testing and Integration testing could be done but something like Selenium is needed for that
As the Application is not that complex, we can rely on the previous unit tests for now and manual testing with the real application and browser
Also we would have to abstract too so many things like cookies and client interaction in unittest, 
    like setting mock cookies which basically makes the test useless as we are not testing the real application
We have decided to not run these in the pipeline for now

class TestAppDashboardRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        from app_dashboard import dashboard_routes
        self.app.register_blueprint(dashboard_routes)
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        with self.client as c:
            with c.session_transaction() as sess:
                sess['logged_in'] = 'admin_session_token'
                store_session('admin_session_token', 'test@example.com', 'user', time.time() + 1800)
                c.set_cookie('logged_in', 'admin_cookie')


    @patch('app_dashboard.get_session_email')
    @patch('app_dashboard.get_session_role')
    def test_user_info(self, mock_get_session_role, mock_get_session_email):
        mock_get_session_email.return_value = 'test@example.com'
        mock_get_session_role.return_value = 'user'
        with self.app.test_request_context('/user_info', environ_overrides={'HTTP_COOKIE': 'logged_in=test_uuid'}):
            response = self.client.get('/user_info')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {'email': 'test@example.com', 'role': 'user'})

    @patch('app_dashboard.map_uuid_to_simulation')
    @patch('app_dashboard.decode_categorical_columns')
    @patch('app_dashboard.reorder_columns')
    @patch('app_dashboard.render_template_with_table')
    def test_open_datatable(self, mock_render_template_with_table, mock_reorder_columns, mock_decode_categorical_columns, mock_map_uuid_to_simulation):
        mock_simulation = MagicMock()
        mock_simulation['data_simulator'].last_120_rows = [MagicMock()]
        mock_map_uuid_to_simulation.return_value = mock_simulation
        mock_render_template_with_table.return_value = 'rendered_template'
        with self.app.test_request_context('/received_data', cookies={'logged_in': 'test_uuid'}):
            response = self.client.get('/received_data')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'rendered_template')

    @patch('app_dashboard.calculate_sha256')
    @patch('app_dashboard.render_template_string')
    def test_model_evaluation(self, mock_render_template_string, mock_calculate_sha256):
        mock_calculate_sha256.return_value = 'dummy_hash'
        mock_render_template_string.return_value = 'rendered_template'
        with self.app.test_request_context('/model_evaluation'):
            response = self.client.get('/model_evaluation')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'rendered_template')

    @patch('app_dashboard.os.path.exists')
    @patch('app_dashboard.send_file')
    def test_download_model(self, mock_send_file, mock_path_exists):
        mock_path_exists.return_value = True
        mock_send_file.return_value = 'file_sent'
        with self.app.test_request_context('/download_model'):
            response = self.client.get('/download_model')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'file_sent')

    @patch('app_dashboard.map_uuid_to_simulation')
    @patch('app_dashboard.initialize_simulation')
    @patch('app_dashboard.get_dashboard_template')
    @patch('app_dashboard.render_template_string')
    def test_dashboard(self, mock_render_template_string, mock_get_dashboard_template, mock_initialize_simulation, mock_map_uuid_to_simulation):
        mock_map_uuid_to_simulation.return_value = None
        mock_initialize_simulation.return_value = None
        mock_get_dashboard_template.return_value = 'dashboard_template'
        mock_render_template_string.return_value = 'rendered_template'
        with self.app.test_request_context('/dashboard', cookies={'logged_in': 'test_uuid'}):
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'rendered_template')
"""

"""
class TestDashboardSocketIOEvents(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.socketio = SocketIO(self.app, logger=False, engineio_logger=False, cors_allowed_origins='*')
        self.client = self.socketio.test_client(self.app)
        self.mock_uuid = 'test_uuid'
        self.mock_simulation = {
            'status': threading.Event(),
            'thread': threading.Thread(),
            'data_simulator': MagicMock()
        }
        # Patch the simulations list
        self.simulations_patcher = patch('app_dashboard.simulations', [(self.mock_uuid, self.mock_simulation)])
        self.simulations_patcher.start()
        # Patch the request cookies
        self.request_patcher = patch('app_dashboard.request')
        self.mock_request = self.request_patcher.start()
        self.mock_request.cookies.get.return_value = self.mock_uuid

    def tearDown(self):
        self.simulations_patcher.stop()
        self.request_patcher.stop()

    def test_start_simulation(self):
        with patch('app_dashboard.socketio.emit') as mock_emit:
            self.client.emit('start_simulation')
            mock_emit.assert_called_with('simulation_status', {'status': 'started'})

    def test_stop_simulation(self):
        with patch('app_dashboard.socketio.emit') as mock_emit:
            self.client.emit('stop_simulation')
            mock_emit.assert_called_with('simulation_status', {'status': 'stopped'})

    def test_reset_data(self):
        self.client.emit('reset_data')
        simulator = self.mock_simulation['data_simulator']
        self.assertEqual(simulator.normal_count, 0)
        self.assertEqual(simulator.bad_count, 0)
        self.assertEqual(len(simulator.last_120_rows), 0)

We dont need to test the training on every test run uncomment if needed

# We dont want to keep training a model in every git pipeline run, if you want to test the training, uncomment the following code
class TestBackendTrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load dataset
        cols = ['duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes', 'land', 'wrong_fragment', 'urgent', 
                'hot', 'num_failed_logins', 'logged_in', 'num_compromised', 'root_shell', 'su_attempted', 'num_root', 
                'num_file_creations', 'num_shells', 'num_access_files', 'num_outbound_cmds', 'is_host_login', 'is_guest_login', 
                'count', 'srv_count', 'serror_rate', 'srv_serror_rate', 'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 
                'diff_srv_rate', 'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate', 
                'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate', 'dst_host_srv_diff_host_rate', 'dst_host_serror_rate', 
                'dst_host_srv_serror_rate', 'dst_host_rerror_rate', 'dst_host_srv_rerror_rate', 'label']
        cls.df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kddcup_data_corrected.csv"), names=cols)

        # Preprocess dataset
        le_encoders = {col: LabelEncoder() for col in ['protocol_type', 'service', 'flag']}
        for col, le in le_encoders.items():
            cls.df[col] = le.fit_transform(cls.df[col])
        cls.label_enc = LabelEncoder()
        cls.df['label'] = cls.label_enc.fit_transform(cls.df['label'])
        scaler = StandardScaler()
        cls.df[cls.df.columns[:-1]] = scaler.fit_transform(cls.df[cls.df.columns[:-1]])

    def test_dataset(self):
        dataset = NetDataset(self.df)
        self.assertEqual(len(dataset), len(self.df))
        features, labels = dataset[0]
        self.assertEqual(features.shape[0], self.df.shape[1] - 1)
        self.assertIsInstance(features, torch.Tensor)
        self.assertIsInstance(labels, torch.Tensor)

    def test_model_initialization(self):
        input_size = self.df.shape[1] - 1
        hidden_size = 128
        output_size = len(self.label_enc.classes_)
        model = SimpleNN(input_size, hidden_size, output_size)
        self.assertEqual(model.fc1.in_features, input_size)
        self.assertEqual(model.fc1.out_features, hidden_size)
        self.assertEqual(model.fc3.out_features, output_size)
    def test_training(self):
        input_size = self.df.shape[1] - 1
        hidden_size = 128
        output_size = len(self.label_enc.classes_)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = SimpleNN(input_size, hidden_size, output_size).to(device)
        opt = torch.optim.Adam(model.parameters(), lr=0.001)
        loss_fn = torch.nn.CrossEntropyLoss()
        dataset = NetDataset(self.df)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        train(model, dataloader, loss_fn, opt, epochs=1, device=device)
        self.assertTrue(model.fc1.weight.grad is not None)

    def test_evaluation(self):
        input_size = self.df.shape[1] - 1
        hidden_size = 128
        output_size = len(self.label_enc.classes_)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = SimpleNN(input_size, hidden_size, output_size).to(device)
        dataset = NetDataset(self.df)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
        evaluate(model, dataloader, device)
        # No assertion here, just ensuring the function runs without errors
""" 

if __name__ == "__main__":
    unittest.main()