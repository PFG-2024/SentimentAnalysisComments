import { useState } from 'react';
import { useRouter } from 'next/router';

const LoginPage = () => {
    const router = useRouter();

    // Estado para almacenar los datos de entrada
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    // Datos de los usuarios (clave codificada en Base64)
    const users = {
        admin: btoa('admin123'), // Contraseña: "admin123"
        joma: btoa('joma456'), // Contraseña: "joma456"
    };

    // Manejar el envío del formulario
    const handleLogin = (e) => {
        e.preventDefault();

        // Validar usuario y contraseña
        if (users[username] && users[username] === btoa(password)) {
            // Redirigir al usuario dependiendo del rol
            if (username === 'admin') {
                router.push('/comentarios');
            } else if (username === 'joma') {
                router.push('/user-dashboard');
            }
        } else {
            setErrorMessage('Usuario o contraseña incorrectos');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
            <div className="bg-white p-8 rounded shadow-md w-full max-w-sm">
                <h1 className="text-2xl font-semibold mb-6 text-center">Iniciar Sesión en Administrador de comentarios</h1>
                {errorMessage && (
                    <p className="text-red-500 text-center mb-4">{errorMessage}</p>
                )}
                <form onSubmit={handleLogin}>
                    <div className="mb-4">
                        <label htmlFor="username" className="block text-gray-700">Usuario</label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <div className="mb-4">
                        <label htmlFor="password" className="block text-gray-700">Contraseña</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
                    >
                        Ingresar
                    </button>
                </form>
            </div>
        </div>
    );
};

export default LoginPage;
