import React, { useState } from "react";
import { Eye, EyeOff, AlertCircle } from "lucide-react";
import Logo from "./cieLogo";
import PESLogo from "./pesLogo";

interface LoginPageProps {
  onLogin: (email: string, password: string) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>(
    {}
  );
  const [isLoading, setIsLoading] = useState(false);

  const validateForm = () => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email) {
      newErrors.email = "SRN is required";
    } else if (email.length !== 13) {
      newErrors.email = "SRN must be exactly 13 characters";
    } else if (!email.toUpperCase().startsWith("PES")) {
      newErrors.email = 'SRN must start with "PES"';
    }

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);

    // Simulate API call
    setTimeout(() => {
      onLogin(email, password);
      setIsLoading(false);
    }, 1000);
  };

  const handleSrnChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase();
    // Limit to 13 characters
    if (value.length <= 13) {
      setEmail(value);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-gradient-to-br from-[#ffffff] to-[#C7C5FF]">
      {/* Background Pattern
      <div className="absolute inset-0 opacity-5">
        <div className="absolute top-20 left-20 w-32 h-32 bg-[#67753A] rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-[#67753A] rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/4 w-24 h-24 bg-[#67753A] rounded-full blur-2xl"></div>
      </div> */}

      {/* Logo */}
      <div className="absolute top-6 left-6 z-10">
        <div className="flex items-center space-x-4">
          <div className="w-50 h-30 flex items-center justify-center transition-all duration-300 hover:scale-105">
            <PESLogo className="w-20 h-18" />
          </div>
          <div className="w-50 h-30 flex items-center justify-center transition-all duration-300 hover:scale-105">
            <Logo className="w-20 h-18" />
          </div>
        </div>
      </div>

      {/* Login Form */}
      <div className="w-full max-w-sm relative z-10">
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl p-6 border border-white/30 transform transition-all duration-500 hover:shadow-3xl">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-[#313c71] mb-1 tracking-tight">
              Welcome Back
            </h1>
            <p className="text-[#313c71]/70 text-sm">
              Sign in to your account to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* SRN Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="block text-sm font-semibold text-[#313c71]"
              >
                SRN
              </label>
              <input
                type="text"
                id="email"
                value={email}
                onChange={handleSrnChange}
                maxLength={13}
                className={`w-full px-3.5 py-3 rounded-xl border-2 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-[#313c71]/10 text-[#313c71] placeholder-[#A2A19B]/50 ${
                  errors.email
                    ? "border-red-400 bg-red-50/50 focus:border-red-500"
                    : "border-[#313c71]/20 bg-white/50 hover:border-[#313c71]/40 focus:border-[#313c71] focus:bg-white"
                }`}
                placeholder="Enter your SRN"
              />
              {errors.email && (
                <div className="flex items-center mt-1.5 text-red-600 text-sm animate-slide-down">
                  <AlertCircle className="w-4 h-4 mr-1.5" />
                  {errors.email}
                </div>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-sm font-semibold text-[#313c71]"
              >
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`w-full px-3.5 py-3 pr-12 rounded-xl border-2 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-[#313c71]/10 text-[#313c71] placeholder-[#A2A19B]/50 ${
                    errors.password
                      ? "border-red-400 bg-red-50/50 focus:border-red-500"
                      : "border-[#313c71]/20 bg-white/50 hover:border-[#313c71]/40 focus:border-[#313c71] focus:bg-white"
                  }`}
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[#313c71]/60 hover:text-[#313c71] transition-colors duration-200 p-1"
                >
                  {showPassword ? (
                    <Eye className="w-5 h-5" />
                  ) : (
                    <EyeOff className="w-5 h-5" />
                  )}
                </button>
              </div>
              {errors.password && (
                <div className="flex items-center mt-1.5 text-red-600 text-sm animate-slide-down">
                  <AlertCircle className="w-4 h-4 mr-1.5" />
                  {errors.password}
                </div>
              )}
            </div>

            {/* Login Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#EF7F1A] text-white py-3 rounded-xl font-semibold text-base hover:bg-[#E75728] active:bg-[#E75728] transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-[#E75728]/20 mt-6"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Signing In...
                </div>
              ) : (
                "Sign In"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
