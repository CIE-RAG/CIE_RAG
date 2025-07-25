import React, { useState } from "react";
import { Eye, EyeOff, AlertCircle } from "lucide-react";
import Logo from "./cieLogo";
import PESLogo from "./pesLogo";
import axios from "axios";

// interface defines the props expected by the login page component
interface LoginPageProps {
  // callback function when login is successful
  //  receives user data with name, email ( labelled srn ) and user_id
  onLogin: (user: { srn: string; name: string; user_id: string }) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  // state for storing user's SRN ( email field )
  const [email, setEmail] = useState("");

  // state for storing user's password
  const [password, setPassword] = useState("");

  // state to hide/show user password
  const [showPassword, setShowPassword] = useState(false);

  // state for storing form validation errors
  // can contain email (srn), password or general messages
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    general?: string;
  }>({});

  // track loading status
  const [isLoading, setIsLoading] = useState(false);

  // login form validation
  // srn must begin with "PES" and the total number of characters must be 13
  // password must be greater than 6 characters
  const validateForm = () => {
    const newErrors: { email?: string; password?: string; general?: string } =
      {};

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

    // update error state
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // handle form submissions
  /** prevents default form submissions
   * validates form inputs
   * makes api calls to login endpoints
   * calls onLogin on callback success
   * displays error messages on failure
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});

    try {
      // make POST request to login api endpoint
      const response = await axios.post(
        "http://localhost:8500/login",
        {
          email,
          password,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      console.log(onLogin, response.data);
      // call the onLogin callback with user data from response
      // TO FIX : might need to fix the onLogin function implementation as was noted in a prev comment
      onLogin(response.data);
    } catch (error) {
      // handle login errors
      let errorMessage = "Failed to login. Please check your SRN and password.";

      // extract error message from API if available
      if (axios.isAxiosError(error)) {
        errorMessage = error.response?.data?.detail || errorMessage;
      }

      // set general error messages
      setErrors({ general: errorMessage });
      console.error("Login error:", error);
    } finally {
      // always reset the loading state
      setIsLoading(false);
    }
  };

  // handling SRN input changes with validation
  const handleSrnChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase();
    if (value.length <= 13) {
      setEmail(value);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-gradient-to-br from-[#ffffff] to-[#C7C5FF]">
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

      {/* main login form container */}
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

          {/* general error message display */}
          {errors.general && (
            <div className="flex items-center mb-4 text-red-600 text-sm animate-slide-down">
              <AlertCircle className="w-4 h-4 mr-1.5" />
              {errors.general}
            </div>
          )}

          {/* login form  */}
          <form onSubmit={handleSubmit} className="space-y-4">
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

              {/* srn validation error */}
              {errors.email && (
                <div className="flex items-center mt-1.5 text-red-600 text-sm animate-slide-down">
                  <AlertCircle className="w-4 h-4 mr-1.5" />
                  {errors.email}
                </div>
              )}
            </div>

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
                  {/* visibility controls for password */}
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* password error */}
              {errors.password && (
                <div className="flex items-center mt-1.5 text-red-600 text-sm animate-slide-down">
                  <AlertCircle className="w-4 h-4 mr-1.5" />
                  {errors.password}
                </div>
              )}
            </div>

            {/* login button */}
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
