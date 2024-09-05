import React from "react";
import { View, Text, Button, Pressable } from "react-native";
import { Link, useRouter } from "expo-router";

// Create a forwardRef button component
const ForwardedButton = React.forwardRef((props: any, ref) => (
  <Pressable ref={ref} {...props}>
    <Text style={{ color: "blue" }}>{props.title}</Text>
  </Pressable>
));

export default function LandingPage() {
  const router = useRouter();

  const handleLogin = () => {
    // Simulate login
    router.replace("/(tabs)/songs");
  };

  return (
    <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
      <Text>Welcome to Guitar Learning App</Text>
      <Link href="/signup" asChild>
        <ForwardedButton title="Sign Up" />
      </Link>
      <Button title="Log In" onPress={handleLogin} />
    </View>
  );
}
