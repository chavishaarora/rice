import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const Profile = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState({
    full_name: "",
    email: "",
    phone: "",
    passport_number: "",
    date_of_birth: "",
    nationality: "",
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await api.getProfile();
      setProfile(data);
    } catch (error: any) {
      toast.error("Failed to load profile");
      console.error(error);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.updateProfile(profile);
      toast.success("Profile updated successfully!");
    } catch (error: any) {
      toast.error("Failed to update profile");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-2xl mx-auto">
        <Button
          variant="ghost"
          onClick={() => navigate("/dashboard")}
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>

        <Card className="p-6 shadow-card">
          <h1 className="text-2xl font-bold text-foreground mb-6">Your Profile</h1>
          <p className="text-sm text-muted-foreground mb-6">
            This information will be used to auto-fill check-in details for flights and hotels.
          </p>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                value={profile.full_name}
                onChange={(e) =>
                  setProfile({ ...profile, full_name: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={profile.email}
                onChange={(e) =>
                  setProfile({ ...profile, email: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <Input
                id="phone"
                type="tel"
                value={profile.phone}
                onChange={(e) =>
                  setProfile({ ...profile, phone: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="passport_number">Passport Number</Label>
              <Input
                id="passport_number"
                value={profile.passport_number}
                onChange={(e) =>
                  setProfile({ ...profile, passport_number: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="date_of_birth">Date of Birth</Label>
              <Input
                id="date_of_birth"
                type="date"
                value={profile.date_of_birth}
                onChange={(e) =>
                  setProfile({ ...profile, date_of_birth: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="nationality">Nationality</Label>
              <Input
                id="nationality"
                value={profile.nationality}
                onChange={(e) =>
                  setProfile({ ...profile, nationality: e.target.value })
                }
              />
            </div>

            <Button
              onClick={handleSave}
              disabled={loading}
              className="w-full mt-6"
            >
              {loading ? "Saving..." : "Save Profile"}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Profile;