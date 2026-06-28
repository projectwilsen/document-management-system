export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="bg-gray-900 p-8 rounded-xl shadow w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold mb-4">Forgot Password?</h1>
        <p className="text-gray-300 mb-4">
          Automated password reset is not yet available.
        </p>
        <p className="text-gray-300">
          Please contact your administrator to reset your password.
        </p>
        <a href="/login" className="mt-6 inline-block text-blue-600 hover:underline">Back to Login</a>
      </div>
    </div>
  );
}
