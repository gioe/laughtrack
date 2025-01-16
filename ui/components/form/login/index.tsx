import React, { useState } from "react";
import PasswordInput from "../../input/password";
import ZipCodeInput from "../../input/zipcode/input";
import FormSubmissionButton from "../../button/form";
import EmailInput from "../../input/email";

const SignupForm = ({ onSubmit, SocialAuthButtons }) => {
    const [formData, setFormData] = useState({
        email: "",
        password: "",
        zipCode: "",
    });
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Basic validation functions (these would be replaced by zod schemas)
    const validateEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const validatePassword = (password) => {
        return password.length >= 8;
    };

    const validateZipCode = (zipCode) => {
        const zipRegex = /^\d{5}$/;
        return zipRegex.test(zipCode);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validate all fields
        const newErrors = {};
        if (!validateEmail(formData.email)) {
            newErrors.email = "Please enter a valid email address";
        }
        if (!validatePassword(formData.password)) {
            newErrors.password = "Password must be at least 8 characters";
        }
        if (!validateZipCode(formData.zipCode)) {
            newErrors.zipCode = "Please enter a valid 5-digit zip code";
        }

        setErrors(newErrors);

        // If no errors, submit the form
        if (Object.keys(newErrors).length === 0) {
            setIsSubmitting(true);
            try {
                await onSubmit(formData);
            } catch (error) {
                console.error("Form submission error:", error);
            } finally {
                setIsSubmitting(false);
            }
        }
    };

    const handleChange = (field) => (e) => {
        setFormData((prev) => ({
            ...prev,
            [field]: e.target.value,
        }));
        // Clear error when user starts typing
        if (errors[field]) {
            setErrors((prev) => ({
                ...prev,
                [field]: "",
            }));
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <EmailInput
                value={formData.email}
                onChange={handleChange("email")}
                label="Email"
                placeholder="Enter your email..."
                className={errors.email ? "border-red-500" : ""}
            />
            {errors.email && (
                <p className="mt-1 text-xs text-red-500">{errors.email}</p>
            )}

            <PasswordInput
                value={formData.password}
                onChange={handleChange("password")}
                label="Password"
                placeholder="Enter your password..."
                className={errors.password ? "border-red-500" : ""}
            />
            {errors.password && (
                <p className="mt-1 text-xs text-red-500">{errors.password}</p>
            )}

            <ZipCodeInput
                value={formData.zipCode}
                onChange={handleChange("zipCode")}
                label="Zip Code"
                placeholder="Enter your zip code..."
                className={errors.zipCode ? "border-red-500" : ""}
            />
            {errors.zipCode && (
                <p className="mt-1 text-xs text-red-500">{errors.zipCode}</p>
            )}

            {/* Divider */}
            <div className="relative">
                <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-white text-gray-500">or</span>
                </div>
            </div>

            {/* Social Login Buttons */}
            {SocialAuthButtons && (
                <SocialAuthButtons
                    onAppleClick={() => {}}
                    onGoogleClick={() => {}}
                />
            )}

            {/* Submit Button */}
            <FormSubmissionButton isLoading={isSubmitting}>
                Sign Up
            </FormSubmissionButton>
        </form>
    );
};

export default SignupForm;
