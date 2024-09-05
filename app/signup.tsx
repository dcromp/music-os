import { View, Text, Button } from "react-native";
import { useRouter } from "expo-router";

export default function SignUpPage() {
  const router = useRouter();

  const handleSignUp = () => {
    // Simulate signup
    router.replace("/(tabs)/songs");
  };

  return (
    <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
      <Text>Sign Up / Log In Page</Text>
      <Button title="Sign Up" onPress={handleSignUp} />
    </View>
  );
}
