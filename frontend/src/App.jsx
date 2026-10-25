import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AdminDashboard from "./pages/AdminDashboard";
import Home from "./pages/Home";
import IssuerCertificates from "./pages/IssuerCertificates";
import IssuerDashboard from "./pages/IssuerDashboard";
import Login from "./pages/Login";
import QrVerification from "./pages/QrVerification";
import RegisterCertificate from "./pages/RegisterCertificate";
import Revocation from "./pages/Revocation";
import StudentCertificateList from "./pages/StudentCertificateList";
import TransactionStatus from "./pages/TransactionStatus";
import VerificationHistory from "./pages/VerificationHistory";
import VerifyCertificate from "./pages/VerifyCertificate";

// All 11 frontend pages from the notes, Section 6:
// Home, Login, Admin Dashboard, Issuer Dashboard, Certificate Registration,
// Student Certificate List, Certificate Verification, Revocation,
// Transaction Status, Verification History, QR Verification.
// Issuer Certificates is the Issuer Dashboard's "Certificates" view.
export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/issuer" element={<IssuerDashboard />} />
          <Route path="/issuer/certificates" element={<IssuerCertificates />} />
          <Route path="/register" element={<RegisterCertificate />} />
          <Route path="/student" element={<StudentCertificateList />} />
          <Route path="/verify" element={<VerifyCertificate />} />
          <Route path="/revoke" element={<Revocation />} />
          <Route path="/transactions" element={<TransactionStatus />} />
          <Route path="/history" element={<VerificationHistory />} />
          <Route path="/qr" element={<QrVerification />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
