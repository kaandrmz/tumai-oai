from supabase import AsyncClient, acreate_client
from app.config import NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SELF_NAME, SELF_URL, SELF_LOGO_URL
from realtime._async.channel import AsyncRealtimeChannel
from typing import Dict

class LogVisService:
    def __init__(self):
        self.url: str | None = NEXT_PUBLIC_SUPABASE_URL
        self.key: str | None = SUPABASE_SERVICE_ROLE_KEY
        self.supabase: AsyncClient | None = None
        self.channels: Dict[str, AsyncRealtimeChannel] = {}
        if not self.url or not self.key:
            print("Warning: Supabase URL or Service Key not properly loaded from config. LogVisService disabled.")

    async def connect(self):
        """Establishes the asynchronous connection to Supabase."""
        if self.supabase:
            print("LogVisService already connected.")
            return
            
        if not self.url or not self.key:
            print("Cannot connect LogVisService: URL or Key missing.")
            return

        try:
            self.supabase = await acreate_client(self.url, self.key)
            await self.register_self()
            print("LogVisService Supabase client initialized.")
        except Exception as e:
            print(f"Error initializing LogVisService Supabase client: {e}")
            self.supabase = None

    async def publish_log(self, session_id: str, payload: dict):
        if not self.supabase:
            print(f"LogVisService Supabase client not initialized, skipping publish for session {session_id}.")
            return

        channel_name = f"session-{session_id}"
        
        try:
            channel = self.channels.get(channel_name)
            
            if not channel:
                print(f"Creating and subscribing to channel: {channel_name}")
                channel = self.supabase.channel(channel_name)
                self.channels[channel_name] = channel
                await channel.subscribe()

            await channel.send_broadcast(
                event="message",
                data=payload
            )
        except AttributeError as ae:
            print(f"AttributeError publishing log to {channel_name}: {ae}. Is the channel object valid?")
        except Exception as e:
            if "before joining" in str(e):
                 print(f"Error publishing to {channel_name}: Still getting 'before joining' error. Investigate channel state management.")
            else:
                 print(f"Error publishing log to Supabase channel {channel_name}: {type(e).__name__}: {e}")

    async def disconnect(self):
        """Disconnects the Supabase realtime client and clears channels."""
        await self.unregister_self()
        
        if self.supabase and hasattr(self.supabase, 'realtime') and self.supabase.realtime.is_connected:
            try:
                print("Disconnecting LogVisService Supabase realtime client...")
                await self.supabase.realtime.disconnect()
                print("LogVisService Supabase realtime client disconnected.")
            except Exception as e:
                print(f"Error disconnecting LogVisService Supabase realtime client: {e}")
        else:
            print("LogVisService Supabase client not initialized or realtime not connected, skipping disconnect.")
        
        # Clear stored channels
        self.channels = {}

    async def register_self(self):
        """Registers the current instance in the "teachers" table.
        
        columns: id, name, url, logo_url
        """
        if not self.supabase:
            print("LogVisService not connected to Supabase, skipping register_self.")
            return

        try:
            await self.supabase.table("teacher").insert({
                "url": SELF_URL,
                "name": SELF_NAME,
                "logo_url": SELF_LOGO_URL
            }).execute()
            print("LogVisService registered in teachers table.")
        except Exception as e:
            print(f"Error registering LogVisService in teachers table: {e}")

    async def unregister_self(self):
        """Unregisters the current instance from the "teachers" table."""
        if not self.supabase:
            print("LogVisService not connected to Supabase, skipping unregister_self.")
            return

        try:
            await self.supabase.table("teacher").delete().eq("name", SELF_NAME).execute()
            print("LogVisService unregistered from teachers table.")
        except Exception as e:
            print(f"Error unregistering LogVisService from teachers table: {e}")
