import { createStackNavigator } from "@react-navigation/stack";
import SongPlayer from "../screens/SongPlayer";
import { RootStackParamList } from "../types/navigation";

const Stack = createStackNavigator<RootStackParamList>();

function AppNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="SongPlayer"
        component={SongPlayer}
        options={{ headerShown: false }}
      />
      {/* Add other screens here */}
    </Stack.Navigator>
  );
}

export default AppNavigator;
