export default function Loading() {
  // You can add any UI inside Loading, including a Skeleton.
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <p className="text-lg font-semibold">正在加载中...</p>
      {/* Add a spinner or skeleton UI here */}
      <div className="mt-4 w-16 h-16 border-4 border-dashed rounded-full animate-spin border-blue-500"></div>
    </div>
  );
}
